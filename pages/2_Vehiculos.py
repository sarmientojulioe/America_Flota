"""Vehículos - ABM, importación masiva y detalle por grupos."""
import streamlit as st
from utils import db, ui, importer

st.set_page_config(page_title="Vehículos | FlotaApp", page_icon="🚑", layout="wide")
ui.aplicar_estilos()
db.require_login()

rol = db.rol_actual()
puede_abm = rol in ("superadmin", "resp_mesa_operativa", "jefe_flota")
st.title("Vehículos")

tab_lista, tab_alta, tab_import = st.tabs(
    ["Listado / Detalle", "Alta de vehículo", "Importar"])

# ============================ ALTA INDIVIDUAL ============================
with tab_alta:
    if not puede_abm:
        st.warning("No tenés permisos para dar de alta vehículos.")
    else:
        with st.form("alta"):
            c1, c2, c3 = st.columns(3)
            dominio = c1.text_input("Dominio *").upper().strip()
            interno = c2.text_input("N° interno")
            tipo = c3.selectbox("Tipo *", db.TIPOS_VEHICULO)
            c4, c5, c6 = st.columns(3)
            marca = c4.text_input("Marca")
            modelo = c5.text_input("Modelo")
            anio = c6.number_input("Año", 1990, 2030, 2020)
            if st.form_submit_button("Crear vehículo"):
                if not dominio:
                    st.error("El dominio es obligatorio.")
                else:
                    try:
                        veh = db.crear_vehiculo(dominio, tipo, marca, modelo, anio, interno)
                        n = len(db.items_vehiculo(veh["id"]))
                        st.success(f"Vehículo {dominio} creado con {n} ítems de control pendientes.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo crear: {e}")

# ============================ IMPORTACIÓN MASIVA ============================
with tab_import:
    if not puede_abm:
        st.warning("No tenés permisos para importar vehículos.")
    else:
        st.caption("Cargá varios vehículos de una vez desde un Excel o CSV. "
                   "Cada vehículo inicializa sus ítems de control según el tipo.")
        COLS = ["dominio", "tipo", "interno", "marca", "modelo", "anio"]
        ejemplo = {"dominio": "AB123CD", "tipo": "ambulancia", "interno": "101",
                   "marca": "Mercedes-Benz", "modelo": "Sprinter", "anio": "2022"}
        st.download_button(
            "📥 Descargar plantilla (Excel)",
            data=importer.plantilla_excel(COLS, ejemplo),
            file_name="plantilla_vehiculos.xlsx", mime=importer.XLSX_MIME)

        up = st.file_uploader("Archivo de vehículos (.xlsx / .csv)",
                              type=["xlsx", "csv"], key="imp_veh")
        if up:
            try:
                df = importer.leer_archivo(up)
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
                st.stop()

            faltan = [c for c in ("dominio", "tipo") if c not in df.columns]
            if faltan:
                st.error(f"Faltan columnas obligatorias: {', '.join(faltan)}. "
                         "Usá la plantilla.")
                st.stop()

            existentes = {v["dominio"].upper() for v in db.vehiculos(activos=False)}
            vistos, filas = set(), []
            for _, r in df.iterrows():
                dom = str(r.get("dominio", "")).upper().strip()
                tip = str(r.get("tipo", "")).lower().strip()
                motivo = ""
                if not dom:
                    motivo = "Dominio vacío"
                elif tip not in db.TIPOS_VEHICULO:
                    motivo = f"Tipo inválido (usar: {', '.join(db.TIPOS_VEHICULO)})"
                elif dom in existentes:
                    motivo = "Ya existe en el sistema"
                elif dom in vistos:
                    motivo = "Dominio duplicado en el archivo"
                vistos.add(dom)
                filas.append({
                    "dominio": dom, "tipo": tip,
                    "interno": str(r.get("interno", "")).strip(),
                    "marca": str(r.get("marca", "")).strip(),
                    "modelo": str(r.get("modelo", "")).strip(),
                    "anio": str(r.get("anio", "")).strip(),
                    "✔": "OK" if not motivo else f"⚠️ {motivo}",
                })

            validas = [f for f in filas if f["✔"] == "OK"]
            st.dataframe(filas, use_container_width=True, hide_index=True)
            st.info(f"{len(validas)} fila(s) válidas de {len(filas)}.")

            if validas and st.button(f"Importar {len(validas)} vehículo(s)"):
                ok, errores = 0, []
                for f in validas:
                    try:
                        db.crear_vehiculo(f["dominio"], f["tipo"], f["marca"],
                                          f["modelo"], f["anio"] or None, f["interno"])
                        ok += 1
                    except Exception as e:
                        errores.append(f"{f['dominio']}: {e}")
                st.success(f"{ok} vehículo(s) importado(s).")
                if errores:
                    st.error("Errores:\n- " + "\n- ".join(errores))
                st.rerun()

# ============================ LISTADO / DETALLE ============================
with tab_lista:
    vehs = db.vehiculos()
    if not vehs:
        st.info("Sin vehículos cargados.")
        st.stop()

    sel = st.selectbox("Vehículo", vehs,
                       format_func=lambda v: f"{v['dominio']} · {v['tipo'].title()} · Int. {v.get('interno') or '-'}")

    # Override manual (solo mesa operativa)
    if rol in ("superadmin", "resp_mesa_operativa"):
        with st.expander("Override de estado (mesa operativa)"):
            opciones = [None, "operativo", "operativo_obs", "fuera_servicio"]
            ov = st.selectbox("Estado manual", opciones,
                              index=opciones.index(sel.get("estado_manual")),
                              format_func=lambda x: "Automático" if x is None else ui.ESTADO_LABEL[x])
            motivo = st.text_input("Motivo", sel.get("motivo_override") or "")
            if st.button("Aplicar override"):
                db.get_client().table("vehiculos").update({
                    "estado_manual": ov, "motivo_override": motivo if ov else None
                }).eq("id", sel["id"]).execute()
                st.rerun()

    # Baja lógica del vehículo (reversible, conserva historial)
    if puede_abm:
        with st.expander("🗑️ Dar de baja este vehículo"):
            st.warning(f"Vas a dar de baja **{sel['dominio']}**. "
                       "Deja de aparecer en listados y controles, pero se conserva el historial. "
                       "Es reversible desde 'Ver vehículos dados de baja'.")
            if st.checkbox(f"Confirmo la baja de {sel['dominio']}", key="conf_baja"):
                if st.button("Dar de baja", type="primary"):
                    db.get_client().table("vehiculos").update(
                        {"activo": False}).eq("id", sel["id"]).execute()
                    st.success(f"{sel['dominio']} dado de baja.")
                    st.rerun()

    # Reactivar vehículos dados de baja
    if puede_abm:
        with st.expander("♻️ Ver vehículos dados de baja"):
            bajas = [v for v in db.vehiculos(activos=False) if not v["activo"]]
            if not bajas:
                st.caption("No hay vehículos dados de baja.")
            else:
                rb = st.selectbox("Vehículo dado de baja", bajas,
                                  format_func=lambda v: f"{v['dominio']} · {v['tipo'].title()}",
                                  key="sel_baja")
                if st.button(f"Reactivar {rb['dominio']}"):
                    db.get_client().table("vehiculos").update(
                        {"activo": True}).eq("id", rb["id"]).execute()
                    st.success(f"{rb['dominio']} reactivado.")
                    st.rerun()

    st.divider()

    items = db.items_vehiculo(sel["id"])
    if not items:
        st.info("Este vehículo no tiene ítems de control asignados.")
    else:
        # Agrupar por grupo
        grupos = {}
        for it in items:
            g = it["items_catalogo"]["grupo_id"]
            grupos.setdefault(g, []).append(it)

        nombres_grupo = {g["id"]: g["nombre"]
                         for g in db.get_client().table("grupos_control").select("*").execute().data}

        for gid, its in sorted(grupos.items()):
            st.subheader(nombres_grupo.get(gid, f"Grupo {gid}"))
            for it in sorted(its, key=lambda x: x["items_catalogo"]["nombre"]):
                cat = it["items_catalogo"]
                color = ui.ITEM_COLOR.get(it["estado"], "#999")
                extra = ""
                if cat["tipo"] == "vencimiento":
                    extra = f"Vence: {it.get('vence_el') or 'sin fecha'}"
                elif cat["tipo"] == "stock":
                    extra = f"Stock: {it.get('cantidad_actual') or 0} / mín {cat.get('cantidad_minima')} {cat.get('unidad') or ''}"
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:6px 10px;"
                    f"border-bottom:1px solid #eee'>"
                    f"<span>{'⚠️ ' if cat['critico'] else ''}{cat['nombre']} "
                    f"<small style='color:#999'>(peso {cat['peso']:.0f})</small></span>"
                    f"<span><small style='color:#666'>{extra}</small> "
                    f"<b style='color:{color}'>{it['estado'].upper()}</b></span></div>",
                    unsafe_allow_html=True)
