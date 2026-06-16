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


TIPOS_VEHICULO = ["ambulancia", "utilitario", "camioneta", "auto", "camion", "otro"]


def crear_vehiculo(dominio, tipo, marca=None, modelo=None, anio=None, interno=None):
    """Crea un vehículo e inicializa sus ítems de control aplicables según el
    tipo (todos en estado 'faltante'). Devuelve el vehículo creado.
    Usado tanto por el alta individual como por la importación masiva."""
    sb = get_client()
    veh = sb.table("vehiculos").insert({
        "dominio": dominio, "interno": interno or None, "tipo": tipo,
        "marca": marca or None, "modelo": modelo or None,
        "anio": int(anio) if anio else None,
    }).execute().data[0]
    grupos = sb.table("grupos_control").select("*").execute().data
    aplicables = [g["id"] for g in grupos
                  if (tipo == "ambulancia" and g["aplica_ambulancia"])
                  or (tipo != "ambulancia" and g["aplica_general"])]
    if aplicables:
        items = (sb.table("items_catalogo").select("id")
                 .in_("grupo_id", aplicables).eq("activo", True).execute().data)
        if items:
            sb.table("vehiculo_items").insert([
                {"vehiculo_id": veh["id"], "item_id": i["id"], "estado": "faltante",
                 "actualizado_por": st.session_state["perfil"]["id"]}
                for i in items]).execute()
    return veh


def crear_grupo(nombre, rol_responsable, aplica_ambulancia=True,
                aplica_general=False, orden=0):
    """Crea un grupo de control. Devuelve el grupo creado."""
    return get_client().table("grupos_control").insert({
        "nombre": nombre, "rol_responsable": rol_responsable,
        "aplica_ambulancia": bool(aplica_ambulancia),
        "aplica_general": bool(aplica_general), "orden": int(orden),
    }).execute().data[0]


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


# ---------------- Bitácora de mantenimiento ----------------
ESTADOS_BITACORA = ["en_proceso", "terminado", "en_seguimiento"]


def bitacoras_de_vehiculo(vehiculo_id):
    return (get_client().table("bitacoras").select("*")
            .eq("vehiculo_id", vehiculo_id)
            .order("nro_bitacora", desc=True).execute().data)


def proximo_nro_bitacora(vehiculo_id) -> int:
    data = (get_client().table("bitacoras").select("nro_bitacora")
            .eq("vehiculo_id", vehiculo_id)
            .order("nro_bitacora", desc=True).limit(1).execute().data)
    return (data[0]["nro_bitacora"] + 1) if data else 1


def guardar_bitacora(campos: dict, bitacora_id=None):
    """Crea (bitacora_id=None) o actualiza una bitácora. Devuelve la fila."""
    sb = get_client()
    if bitacora_id:
        campos["actualizado_en"] = "now()"
        return sb.table("bitacoras").update(campos).eq("id", bitacora_id).execute().data[0]
    campos["creado_por"] = st.session_state["perfil"]["id"]
    return sb.table("bitacoras").insert(campos).execute().data[0]
