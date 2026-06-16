"""Vencimientos próximos - integrable con n8n para alertas."""
import streamlit as st
import pandas as pd
from utils import db, ui

st.set_page_config(page_title="Vencimientos | FlotaApp", page_icon="📅", layout="wide")
ui.aplicar_estilos()
db.require_login()

st.title("Vencimientos")

dias = st.slider("Mostrar vencimientos dentro de los próximos (días)", 7, 180, 60)
data = db.vencimientos(dias)

if not data:
    st.success("Sin vencimientos en el período seleccionado. 🎉")
    st.stop()

df = pd.DataFrame(data)
df = df.rename(columns={
    "dominio": "Dominio", "interno": "Interno", "tipo_vehiculo": "Tipo",
    "grupo": "Grupo", "item": "Ítem", "vence_el": "Vence",
    "dias_restantes": "Días", "estado": "Estado",
})


def color_fila(row):
    if row["Días"] < 0:
        return ["background-color: #fdecea"] * len(row)
    if row["Días"] <= 15:
        return ["background-color: #fef6e7"] * len(row)
    return [""] * len(row)


st.dataframe(df.style.apply(color_fila, axis=1), use_container_width=True, hide_index=True)

st.caption("💡 La vista `v_vencimientos` está disponible en Supabase para conectar "
           "alertas automáticas desde n8n (mismo patrón que inspecciones/calibraciones).")
