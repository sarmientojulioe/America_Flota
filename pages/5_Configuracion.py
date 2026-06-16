"""Configuración - catálogo de ítems, pesos y grupos de control."""
import streamlit as st
import pandas as pd
from utils import db, ui

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
