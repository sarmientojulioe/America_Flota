"""Dashboard - semáforo de flota."""
import streamlit as st
from utils import db, ui

st.set_page_config(page_title="Dashboard | FlotaApp", page_icon="🚑", layout="wide")
ui.aplicar_estilos()
db.require_login()

perfil = st.session_state["perfil"]
st.sidebar.markdown(f"**{perfil['nombre']}**  \n_{perfil['rol'].replace('_',' ').title()}_")
if st.sidebar.button("Cerrar sesión"):
    db.logout()
    st.switch_page("app.py")

st.title("Estado de Flota")

flota = db.flota_estado()
if not flota:
    st.info("No hay vehículos cargados. Agregalos desde **Vehículos**.")
    st.stop()

# KPIs
total = len(flota)
operativos = sum(1 for v in flota if v["estado_efectivo"] == "operativo")
con_obs = sum(1 for v in flota if v["estado_efectivo"] == "operativo_obs")
fuera = sum(1 for v in flota if v["estado_efectivo"] == "fuera_servicio")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total flota", total)
c2.metric("Operativos", operativos)
c3.metric("Con observaciones", con_obs)
c4.metric("Fuera de servicio", fuera)

st.divider()

# Filtros
fc1, fc2 = st.columns([1, 1])
tipo_f = fc1.selectbox("Tipo", ["Todos"] + sorted({v["tipo"] for v in flota}))
estado_f = fc2.selectbox("Estado", ["Todos", "operativo", "operativo_obs", "fuera_servicio"],
                         format_func=lambda x: ui.ESTADO_LABEL.get(x, x))

filtrada = [v for v in flota
            if (tipo_f == "Todos" or v["tipo"] == tipo_f)
            and (estado_f == "Todos" or v["estado_efectivo"] == estado_f)]

# Ordenar: peor disponibilidad primero
for v in sorted(filtrada, key=lambda x: x["disponibilidad"]):
    ui.card_vehiculo(v)
