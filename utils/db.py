"""Conexión a Supabase y helpers de datos - FlotaApp."""
import streamlit as st
from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions

from utils import ui


@st.cache_resource
def get_client() -> Client:
    # schema="flota": las tablas de la app viven en el schema dedicado "flota",
    # separado del proyecto "cotizaciones" que ocupa public en la misma instancia.
    # SyncClientOptions (no el ClientOptions base) es el que espera el cliente sync:
    # trae el campo `storage` requerido para persistir la sesión.
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
        options=SyncClientOptions(schema="flota"),
    )


# ---------------- Auth ----------------
def login(email: str, password: str):
    sb = get_client()
    res = sb.auth.sign_in_with_password({"email": email, "password": password})
    perfil = sb.table("perfiles").select("*").eq("id", res.user.id).single().execute()
    return res.user, perfil.data


def logout():
    get_client().auth.sign_out()
    for k in ("user", "perfil"):
        st.session_state.pop(k, None)


def require_login():
    if "perfil" not in st.session_state:
        st.switch_page("app.py")
    ui.sidebar_footer()


def rol_actual() -> str:
    return st.session_state.get("perfil", {}).get("rol", "")


# ---------------- Datos ----------------
def flota_estado():
    return get_client().table("v_flota_estado").select("*").execute().data


def vehiculos(activos=True):
    q = get_client().table("vehiculos").select("*").order("dominio")
    if activos:
        q = q.eq("activo", True)
    return q.execute().data


def grupos_para_rol(rol: str):
    sb = get_client()
    q = sb.table("grupos_control").select("*").order("orden")
    if rol not in ("superadmin", "resp_mesa_operativa"):
        q = q.eq("rol_responsable", rol)
    return q.execute().data


def items_de_grupo(grupo_id: int):
    return (get_client().table("items_catalogo").select("*")
            .eq("grupo_id", grupo_id).eq("activo", True)
            .order("nombre").execute().data)


def items_vehiculo(vehiculo_id: int, grupo_id: int | None = None):
    sb = get_client()
    q = (sb.table("vehiculo_items")
         .select("*, items_catalogo(*)")
         .eq("vehiculo_id", vehiculo_id))
    data = q.execute().data
    if grupo_id:
        data = [d for d in data if d["items_catalogo"]["grupo_id"] == grupo_id]
    return data


def upsert_item_vehiculo(vehiculo_id, item_id, **campos):
    sb = get_client()
    campos.update({
        "vehiculo_id": vehiculo_id,
        "item_id": item_id,
        "actualizado_por": st.session_state["perfil"]["id"],
        "actualizado_en": "now()",
    })
    return sb.table("vehiculo_items").upsert(
        campos, on_conflict="vehiculo_id,item_id").execute()


def registrar_control(vehiculo_id, grupo_id, observaciones, detalles: list[dict]):
    """detalles: [{item_id, estado, cantidad_registrada, vence_el, observacion}]"""
    sb = get_client()
    ctrl = sb.table("controles").insert({
        "vehiculo_id": vehiculo_id,
        "grupo_id": grupo_id,
        "usuario_id": st.session_state["perfil"]["id"],
        "observaciones": observaciones,
    }).execute().data[0]
    for d in detalles:
        d["control_id"] = ctrl["id"]
    if detalles:
        sb.table("controles_detalle").insert(detalles).execute()
    return ctrl


def vencimientos(dias=60):
    data = get_client().table("v_vencimientos").select("*").execute().data
    return [d for d in data if d["dias_restantes"] is not None and d["dias_restantes"] <= dias]
