"""Configuración - catálogo de ítems, pesos y grupos de control."""
import streamlit as st
import pandas as pd
from utils import db, ui, importer

st.set_page_config(page_title="Configuración | FlotaApp", page_icon="⚙️", layout="wide")
ui.aplicar_estilos()
db.require_login()

rol = db.rol_actual()
es_admin = rol in ("superadmin", "resp_mesa_operativa")
st.title("Configuración del catálogo")

sb = db.get_client()
grupos = sb.table("grupos_control").select("*").order("orden").execute().data
grupos_por_nombre = {g["nombre"]: g["id"] for g in grupos}
ROLES = ["jefe_flota", "mecanico", "enfermero", "bioingeniero",
         "resp_mesa_operativa", "superadmin"]

# ============ Crear grupo nuevo (solo mesa operativa / superadmin) ============
if es_admin:
    with st.expander("➕ Crear grupo de control nuevo"):
        with st.form("nuevo_grupo"):
            g1, g2 = st.columns(2)
            g_nombre = g1.text_input("Nombre del grupo *")
            g_rol = g2.selectbox("Rol responsable", ROLES, index=0)
            g3, g4, g5 = st.columns(3)
            g_amb = g3.checkbox("Aplica a ambulancias", value=True)
            g_gen = g4.checkbox("Aplica a otros vehículos")
            g_orden = g5.number_input("Orden", 0, 99, len(grupos) + 1)
            if st.form_submit_button("Crear grupo"):
                if not g_nombre.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    sb.table("grupos_control").insert({
                        "nombre": g_nombre.strip(), "rol_responsable": g_rol,
                        "aplica_ambulancia": g_amb, "aplica_general": g_gen,
                        "orden": int(g_orden),
                    }).execute()
                    st.success(f"Grupo '{g_nombre}' creado.")
                    st.rerun()

    with st.expander("📥 Importar grupos desde Excel/CSV"):
        COLS = ["nombre", "rol_responsable", "aplica_ambulancia", "aplica_general", "orden"]
        ejemplo = {"nombre": "Seguridad", "rol_responsable": "jefe_flota",
                   "aplica_ambulancia": "si", "aplica_general": "si", "orden": "6"}
        st.download_button("📥 Descargar plantilla (Excel)",
                           data=importer.plantilla_excel(COLS, ejemplo),
                           file_name="plantilla_grupos.xlsx", mime=importer.XLSX_MIME,
                           key="tpl_grupos")
        up = st.file_uploader("Archivo de grupos (.xlsx / .csv)",
                              type=["xlsx", "csv"], key="imp_grupos")
        if up:
            try:
                df = importer.leer_archivo(up)
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
                st.stop()
            if "nombre" not in df.columns or "rol_responsable" not in df.columns:
                st.error("Faltan columnas obligatorias: nombre, rol_responsable.")
                st.stop()
            nombres_exist = {g["nombre"].lower() for g in grupos}
            vistos, filas = set(), []
            for _, r in df.iterrows():
                nom = str(r.get("nombre", "")).strip()
                rl = str(r.get("rol_responsable", "")).strip().lower()
                motivo = ""
                if not nom:
                    motivo = "Nombre vacío"
                elif rl not in ROLES:
                    motivo = f"Rol inválido (usar: {', '.join(ROLES)})"
                elif nom.lower() in nombres_exist:
                    motivo = "Ya existe"
                elif nom.lower() in vistos:
                    motivo = "Duplicado en el archivo"
                vistos.add(nom.lower())
                filas.append({
                    "nombre": nom, "rol_responsable": rl,
                    "aplica_ambulancia": importer.parse_bool(r.get("aplica_ambulancia", "si")),
                    "aplica_general": importer.parse_bool(r.get("aplica_general", "no")),
                    "orden": str(r.get("orden", "")).strip(),
                    "✔": "OK" if not motivo else f"⚠️ {motivo}",
                })
            validas = [f for f in filas if f["✔"] == "OK"]
            st.dataframe(filas, use_container_width=True, hide_index=True)
            st.info(f"{len(validas)} fila(s) válidas de {len(filas)}.")
            if validas and st.button(f"Importar {len(validas)} grupo(s)"):
                ok, errores = 0, []
                for f in validas:
                    try:
                        orden = int(f["orden"]) if f["orden"].isdigit() else 0
                        db.crear_grupo(f["nombre"], f["rol_responsable"],
                                       f["aplica_ambulancia"], f["aplica_general"], orden)
                        ok += 1
                    except Exception as e:
                        errores.append(f"{f['nombre']}: {e}")
                st.success(f"{ok} grupo(s) importado(s).")
                if errores:
                    st.error("Errores:\n- " + "\n- ".join(errores))
                st.rerun()

# Cada responsable edita su grupo; mesa operativa y superadmin editan todo
editables = grupos if es_admin else [g for g in grupos if g["rol_responsable"] == rol]
if not editables:
    st.warning("Tu rol no puede editar el catálogo.")
    st.stop()

st.divider()
grupo = st.selectbox("Grupo", editables, format_func=lambda g: g["nombre"])
ver_inactivos = st.checkbox("Ver ítems inactivos", value=False)

# Traigo los ítems del grupo (incluyendo inactivos si se pide)
q = sb.table("items_catalogo").select("*").eq("grupo_id", grupo["id"]).order("nombre")
items = q.execute().data
if not ver_inactivos:
    items = [i for i in items if i["activo"]]

st.subheader(f"Ítems de {grupo['nombre']}")

# Grupos a los que el usuario puede MOVER ítems (a los que puede escribir)
grupos_destino = [g["nombre"] for g in (grupos if es_admin
                  else [x for x in grupos if x["rol_responsable"] == rol])]

if items:
    df = pd.DataFrame(items)
    df["grupo"] = grupo["nombre"]
    df = df[["id", "nombre", "tipo", "grupo", "activo", "peso", "critico",
             "dias_alerta", "cantidad_minima", "unidad"]]
    edited = st.data_editor(
        df, hide_index=True, use_container_width=True,
        disabled=["id", "nombre", "tipo"],
        column_config={
            "grupo": st.column_config.SelectboxColumn(
                "Grupo", options=grupos_destino,
                help="Cambialo para mover el ítem a otro grupo"),
            "activo": st.column_config.CheckboxColumn(
                "Activo", help="Desmarcá para desactivar el ítem"),
            "peso": st.column_config.NumberColumn("Peso (0-100)", min_value=0, max_value=100),
            "critico": st.column_config.CheckboxColumn("Crítico"),
            "dias_alerta": st.column_config.NumberColumn("Días alerta"),
            "cantidad_minima": st.column_config.NumberColumn("Cant. mínima"),
        })
    if st.button("💾 Guardar cambios"):
        movidos = 0
        for _, row in edited.iterrows():
            campos = {
                "peso": float(row["peso"]),
                "critico": bool(row["critico"]),
                "activo": bool(row["activo"]),
                "dias_alerta": int(row["dias_alerta"]) if pd.notna(row["dias_alerta"]) else None,
                "cantidad_minima": float(row["cantidad_minima"]) if pd.notna(row["cantidad_minima"]) else None,
                "unidad": row["unidad"] if pd.notna(row["unidad"]) else None,
            }
            nuevo_grupo_id = grupos_por_nombre.get(row["grupo"])
            if nuevo_grupo_id and nuevo_grupo_id != grupo["id"]:
                campos["grupo_id"] = nuevo_grupo_id
                movidos += 1
            sb.table("items_catalogo").update(campos).eq("id", int(row["id"])).execute()
        msg = "Catálogo actualizado."
        if movidos:
            msg += f" {movidos} ítem(s) movido(s) de grupo."
        st.success(msg)
        st.rerun()
else:
    st.info("Este grupo no tiene ítems." + ("" if ver_inactivos else " (probá 'Ver ítems inactivos')"))

st.divider()
with st.expander("➕ Agregar ítem nuevo"):
    with st.form("nuevo_item"):
        c1, c2, c3 = st.columns(3)
        nombre = c1.text_input("Nombre *")
        tipo = c2.selectbox("Tipo", ["vencimiento", "stock", "checklist"])
        peso = c3.number_input("Peso", 0.0, 100.0, 10.0)
        c4, c5, c6 = st.columns(3)
        critico = c4.checkbox("Crítico")
        dias_alerta = c5.number_input("Días alerta (vencimiento)", 0, 365, 30)
        cant_min = c6.number_input("Cantidad mínima (stock)", 0.0, step=1.0)
        unidad = st.text_input("Unidad (stock)", "unidades")
        if st.form_submit_button("Crear ítem"):
            if not nombre:
                st.error("El nombre es obligatorio.")
            else:
                sb.table("items_catalogo").insert({
                    "grupo_id": grupo["id"], "nombre": nombre, "tipo": tipo,
                    "peso": peso, "critico": critico,
                    "dias_alerta": dias_alerta if tipo == "vencimiento" else None,
                    "cantidad_minima": cant_min if tipo == "stock" else None,
                    "unidad": unidad if tipo == "stock" else None,
                }).execute()
                st.success(f"Ítem '{nombre}' creado. Asignalo a los vehículos existentes desde Vehículos.")
                st.rerun()
