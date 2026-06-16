"""Mi Control - checklist del grupo según rol logueado."""
import streamlit as st
from datetime import date
from utils import db, ui

st.set_page_config(page_title="Mi Control | FlotaApp", page_icon="✅", layout="wide")
ui.aplicar_estilos()
db.require_login()

rol = db.rol_actual()
st.title("Realizar Control")

grupos = db.grupos_para_rol(rol)
if not grupos:
    st.warning("Tu rol no tiene grupos de control asignados.")
    st.stop()

grupo = st.selectbox("Grupo de control", grupos, format_func=lambda g: g["nombre"])

vehs = db.vehiculos()
if grupo and not grupo["aplica_general"]:
    vehs = [v for v in vehs if v["tipo"] == "ambulancia"]

if not vehs:
    st.info("No hay vehículos aplicables para este grupo.")
    st.stop()

veh = st.selectbox("Vehículo", vehs,
                   format_func=lambda v: f"{v['dominio']} · Int. {v.get('interno') or '-'} · {v['disponibilidad']:.0f}%")

st.divider()
st.subheader(f"{grupo['nombre']} — {veh['dominio']}")

items_estado = {i["item_id"]: i for i in db.items_vehiculo(veh["id"], grupo["id"])}
catalogo = db.items_de_grupo(grupo["id"])

resultados = {}
with st.form("control"):
    for cat in catalogo:
        actual = items_estado.get(cat["id"], {})
        cols = st.columns([3, 2, 2])
        critico = "⚠️ " if cat["critico"] else ""
        cols[0].markdown(f"**{critico}{cat['nombre']}**  \n"
                         f"<small style='color:#999'>peso {cat['peso']:.0f}</small>",
                         unsafe_allow_html=True)

        if cat["tipo"] == "vencimiento":
            vence = cols[1].date_input("Vence", value=actual.get("vence_el") and date.fromisoformat(actual["vence_el"]) or None,
                                       key=f"v_{cat['id']}", format="DD/MM/YYYY")
            resultados[cat["id"]] = {"tipo": "vencimiento", "vence_el": str(vence) if vence else None}
        elif cat["tipo"] == "stock":
            cant = cols[1].number_input(f"Cantidad ({cat.get('unidad') or 'u'})",
                                        min_value=0.0, step=1.0,
                                        value=float(actual.get("cantidad_actual") or 0),
                                        key=f"c_{cat['id']}")
            vence_med = None
            if grupo["nombre"] == "Medicamentos":
                vence_med = cols[2].date_input("Próx. vto", value=actual.get("vence_el") and date.fromisoformat(actual["vence_el"]) or None,
                                               key=f"vm_{cat['id']}", format="DD/MM/YYYY")
            resultados[cat["id"]] = {"tipo": "stock", "cantidad_actual": cant,
                                     "vence_el": str(vence_med) if vence_med else None}
        else:  # checklist
            ok = cols[1].radio("Estado", ["ok", "alerta", "faltante"],
                               index=["ok", "alerta", "faltante"].index(actual.get("estado", "ok"))
                               if actual.get("estado") in ("ok", "alerta", "faltante") else 0,
                               key=f"r_{cat['id']}", horizontal=True)
            resultados[cat["id"]] = {"tipo": "checklist", "estado": ok}

    obs = st.text_area("Observaciones generales del control")
    enviar = st.form_submit_button("✅ Registrar control", use_container_width=True)

if enviar:
    detalles = []
    for item_id, r in resultados.items():
        cat = next(c for c in catalogo if c["id"] == item_id)
        campos = {}
        if r["tipo"] == "vencimiento":
            ve = r["vence_el"]
            if not ve:
                estado = "faltante"
            elif date.fromisoformat(ve) < date.today():
                estado = "vencido"
            elif (date.fromisoformat(ve) - date.today()).days <= (cat.get("dias_alerta") or 30):
                estado = "alerta"
            else:
                estado = "ok"
            campos = {"vence_el": ve, "estado": estado}
        elif r["tipo"] == "stock":
            cant = r["cantidad_actual"]
            minimo = cat.get("cantidad_minima") or 0
            if cant <= 0:
                estado = "faltante"
            elif cant < minimo:
                estado = "alerta"
            else:
                estado = "ok"
            # Medicamento vencido pisa el estado de stock
            if r.get("vence_el") and date.fromisoformat(r["vence_el"]) < date.today():
                estado = "vencido"
            campos = {"cantidad_actual": cant, "vence_el": r.get("vence_el"), "estado": estado}
        else:
            estado = r["estado"]
            campos = {"estado": estado}

        db.upsert_item_vehiculo(veh["id"], item_id, **campos)
        detalles.append({"item_id": item_id, "estado": estado,
                         "cantidad_registrada": campos.get("cantidad_actual"),
                         "vence_el": campos.get("vence_el")})

    db.registrar_control(veh["id"], grupo["id"], obs, detalles)
    st.success("Control registrado. La disponibilidad del vehículo se recalculó automáticamente.")
    st.balloons()
