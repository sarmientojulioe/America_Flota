"""FlotaApp - Control de Flota y Disponibilidad | American Advisor."""
import streamlit as st
from utils import db, ui

st.set_page_config(page_title="FlotaApp | American Advisor",
                   page_icon="🚑", layout="wide")
ui.aplicar_estilos()

if "perfil" in st.session_state:
    st.switch_page("pages/1_Dashboard.py")

st.markdown(f"<h1 style='color:{ui.NAVY}'>FlotaApp</h1>"
            f"<p style='color:{ui.BLUE_MED}; font-weight:600'>"
            "Control de flota y disponibilidad · Mesa Operativa</p>",
            unsafe_allow_html=True)

with st.form("login"):
    email = st.text_input("Email")
    password = st.text_input("Contraseña", type="password")
    if st.form_submit_button("Ingresar", use_container_width=True):
        try:
            user, perfil = db.login(email, password)
            if not perfil["activo"]:
                st.error("Usuario inactivo. Contactá al administrador.")
            else:
                st.session_state["user"] = user
                st.session_state["perfil"] = perfil
                st.rerun()
        except Exception as e:
            msg = str(e).lower()
            if "invalid" in msg or "credential" in msg:
                st.error("Credenciales inválidas.")
            else:
                st.error(f"No se pudo iniciar sesión: {e}")

st.divider()
st.markdown(ui.isologos(height=44), unsafe_allow_html=True)
st.caption("American Advisor · Sistema de gestión certificado ISO 9001 · 14001 · 45001")
