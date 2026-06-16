"""Vehículos - ABM y detalle por grupos."""
import streamlit as st
from utils import db, ui

st.set_page_config(page_title="Vehículos | FlotaApp", page_icon="🚑", layout="wide")
ui.aplicar_estilos()
db.require_login()

rol = db.rol_actual()
st.title("Vehículos")

tab_lista, tab_alta = st.tabs(["Listado / Detalle", "Alta de vehículo"])

with tab_alta:
    if rol not in ("superadmin", "resp_mesa_operativa", "jefe_flota"):
        st.warning("No tenés permisos para dar de alta vehículos.")
    else:
        with st.form("alta"):
            c1, c2, c3 = st.columns(3)
            dominio = c1.text_input("Dominio *").upper().strip()
            interno = c2.text_input("N° interno")
            tipo = c3.selectbox("Tipo *", ["ambulancia", "utilitario", "camioneta", "auto", "camion", "otro"])
            c4, c5, c6 = st.columns(3)
            marca = c4.text_input("Marca")
            modelo = c5.text_input("Modelo")
            anio = c6.number_input("Año", 1990, 2030, 2020)
            if st.form_submit_button("Crear vehículo"):
                if not dominio:
                    st.error("El dominio es obligatorio.")
                else:
                    sb = db.get_client()
                    veh = sb.table("vehiculos").insert({
                        "dominio": dominio, "interno": interno, "tipo": tipo,
                        "marca": marca, "modelo": modelo, "anio": int(anio),
                    }).execute().data[0]
                    # Inicializar ítems aplicables
                    grupos = sb.table("grupos_control").select("*").execute().data
                    aplicables = [g["id"] for g in grupos
                                  if (tipo == "ambulancia" and g["aplica_ambulancia"])
                                  or (tipo != "ambulancia" and g["aplica_general"])]
                    items = (sb.table("items_catalogo").select("id")
                             .in_("grupo_id", aplicables).eq("activo", True).execute().data)
                    if items:
                        sb.table("vehiculo_items").insert([
                            {"vehiculo_id": veh["id"], "item_id": i["id"],
                             "estado": "faltante",
                             "actualizado_por": st.session_state["perfil"]["id"]}
                            for i in items]).execute()
                    st.success(f"Vehículo {dominio} creado con {len(items)} ítems de control pendientes.")
                    st.rerun()

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
