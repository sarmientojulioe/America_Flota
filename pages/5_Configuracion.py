"""Configuración - catálogo de ítems y pesos."""
import streamlit as st
import pandas as pd
from utils import db, ui

st.set_page_config(page_title="Configuración | FlotaApp", page_icon="⚙️", layout="wide")
ui.aplicar_estilos()
db.require_login()

rol = db.rol_actual()
st.title("Configuración del catálogo")

sb = db.get_client()
grupos = sb.table("grupos_control").select("*").order("orden").execute().data

# Cada responsable edita su grupo; mesa operativa y superadmin editan todo
if rol in ("superadmin", "resp_mesa_operativa"):
    editables = grupos
else:
    editables = [g for g in grupos if g["rol_responsable"] == rol]

if not editables:
    st.warning("Tu rol no puede editar el catálogo.")
    st.stop()

grupo = st.selectbox("Grupo", editables, format_func=lambda g: g["nombre"])

items = db.items_de_grupo(grupo["id"])
st.subheader(f"Ítems de {grupo['nombre']}")

if items:
    df = pd.DataFrame(items)[["id", "nombre", "tipo", "peso", "critico",
                              "dias_alerta", "cantidad_minima", "unidad"]]
    edited = st.data_editor(
        df, hide_index=True, use_container_width=True,
        disabled=["id", "nombre", "tipo"],
        column_config={
            "peso": st.column_config.NumberColumn("Peso (0-100)", min_value=0, max_value=100),
            "critico": st.column_config.CheckboxColumn("Crítico"),
            "dias_alerta": st.column_config.NumberColumn("Días alerta"),
            "cantidad_minima": st.column_config.NumberColumn("Cant. mínima"),
        })
    if st.button("💾 Guardar cambios"):
        for _, row in edited.iterrows():
            sb.table("items_catalogo").update({
                "peso": float(row["peso"]),
                "critico": bool(row["critico"]),
                "dias_alerta": int(row["dias_alerta"]) if pd.notna(row["dias_alerta"]) else None,
                "cantidad_minima": float(row["cantidad_minima"]) if pd.notna(row["cantidad_minima"]) else None,
                "unidad": row["unidad"] if pd.notna(row["unidad"]) else None,
            }).eq("id", int(row["id"])).execute()
        st.success("Catálogo actualizado.")

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
