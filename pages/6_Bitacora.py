"""Bitácora de Mantenimiento (ISO R SR 07) - carga e historial por móvil."""
import streamlit as st
from datetime import date
from utils import db, ui

st.set_page_config(page_title="Bitácora | FlotaApp", page_icon="🛠️", layout="wide")
ui.aplicar_estilos()
db.require_login()

rol = db.rol_actual()
puede_mant = rol in ("superadmin", "resp_mesa_operativa", "jefe_flota", "mecanico")
st.title("Bitácora de Mantenimiento")
st.caption("Registro de intervenciones de mantenimiento por móvil · ISO R SR 07")

vehs = db.vehiculos()
if not vehs:
    st.info("No hay vehículos cargados.")
    st.stop()

veh = st.selectbox("Móvil", vehs,
                   format_func=lambda v: f"{v['dominio']} · {v['tipo'].title()} · Int. {v.get('interno') or '-'}")

NATURALEZAS = ["", "Sanitario", "Mecánico", "Eléctrico", "Sanitario/Mecánico", "Otro"]
CLASES = ["", "Preventivo", "Correctivo", "Modificación", "Registral"]
ESTADO_LABEL = {"en_proceso": "En proceso", "terminado": "Proceso terminado",
                "en_seguimiento": "En seguimiento"}

tab_nueva, tab_hist = st.tabs(["Nueva bitácora", "Historial"])


def _form_bitacora(veh, datos=None, bitacora_id=None):
    """Formulario de alta/edición. datos=None => alta."""
    d = datos or {}
    nro = d.get("nro_bitacora") or db.proximo_nro_bitacora(veh["id"])
    with st.form(f"bitacora_{bitacora_id or 'nueva'}"):
        st.markdown(f"**Bitácora N° {nro}** — {veh['dominio']} · {veh.get('marca') or ''} {veh.get('modelo') or ''}")

        c1, c2, c3 = st.columns(3)
        fecha = c1.date_input("Fecha de bitácora",
                              value=date.fromisoformat(d["fecha_bitacora"]) if d.get("fecha_bitacora") else date.today(),
                              format="DD/MM/YYYY")
        lugar = c2.text_input("Lugar de prestación", d.get("lugar_prestacion") or "")
        estado = c3.selectbox("Estado", db.ESTADOS_BITACORA,
                              index=db.ESTADOS_BITACORA.index(d.get("estado", "en_proceso")),
                              format_func=lambda x: ESTADO_LABEL[x])

        st.markdown("**Técnico encargado**")
        t1, t2, t3 = st.columns(3)
        tec_nombre = t1.text_input("Nombre y apellido", d.get("tecnico_nombre") or "")
        tec_tel = t2.text_input("Teléfono", d.get("tecnico_telefono") or "")
        tec_pert = t3.text_input("Pertenece a", d.get("tecnico_pertenece") or "")

        st.markdown("**Elemento / equipo intervenido**")
        desc = st.text_area("Descripción detallada del elemento", d.get("descripcion_elemento") or "")
        valid = st.text_input("Validación", d.get("validacion") or "")

        st.markdown("**Tiempos**")
        x1, x2, x3, x4 = st.columns(4)
        fparada = x1.date_input("Fecha de parada",
                                value=date.fromisoformat(d["fecha_parada"]) if d.get("fecha_parada") else None,
                                format="DD/MM/YYYY")
        hini = x2.text_input("Hora inicio", d.get("hora_inicio") or "")
        hfin = x3.text_input("Hora finalización", d.get("hora_fin") or "")
        total = x4.text_input("Total en hs.", d.get("total_hs") or "")
        y1, y2, y3 = st.columns(3)
        parada = y1.text_input("Parada", d.get("parada") or "")
        gestion = y2.text_input("Gestión de abastecimiento", d.get("gestion_abastecimiento") or "")
        comienzo = y3.text_input("Comienzo de la acción", d.get("comienzo_accion") or "")

        st.markdown("**Clasificación**")
        z1, z2, z3 = st.columns(3)
        nat = z1.selectbox("Naturaleza", NATURALEZAS,
                           index=NATURALEZAS.index(d["naturaleza"]) if d.get("naturaleza") in NATURALEZAS else 0)
        clase = z2.selectbox("Clase", CLASES,
                             index=CLASES.index(d["clase"]) if d.get("clase") in CLASES else 0)
        tipom = z3.text_input("Tipo de mantenimiento", d.get("tipo_mantenimiento") or "")

        st.markdown("**Costos**")
        k1, k2 = st.columns(2)
        costo = k1.number_input("Costo", min_value=0.0, step=100.0,
                                value=float(d.get("costo") or 0))
        proveedor = k2.text_input("Proveedor", d.get("proveedor") or "")

        st.markdown("**Detalle**")
        observa = st.text_area("Se observa", d.get("se_observa") or "")
        acciones = st.text_area("Acciones", d.get("acciones") or "")
        obs = st.text_area("Observaciones", d.get("observaciones") or "")
        valaut = st.text_input("Validación / Autorización", d.get("validacion_autorizacion") or "")

        guardar = st.form_submit_button("💾 Guardar bitácora", use_container_width=True)

    if guardar:
        campos = {
            "vehiculo_id": veh["id"], "nro_bitacora": int(nro),
            "fecha_bitacora": str(fecha), "lugar_prestacion": lugar or None,
            "estado": estado,
            "tecnico_nombre": tec_nombre or None, "tecnico_telefono": tec_tel or None,
            "tecnico_pertenece": tec_pert or None,
            "descripcion_elemento": desc or None, "validacion": valid or None,
            "fecha_parada": str(fparada) if fparada else None,
            "hora_inicio": hini or None, "hora_fin": hfin or None, "total_hs": total or None,
            "parada": parada or None, "gestion_abastecimiento": gestion or None,
            "comienzo_accion": comienzo or None,
            "naturaleza": nat or None, "clase": clase or None,
            "tipo_mantenimiento": tipom or None,
            "costo": costo or None, "proveedor": proveedor or None,
            "se_observa": observa or None, "acciones": acciones or None,
            "observaciones": obs or None, "validacion_autorizacion": valaut or None,
        }
        try:
            db.guardar_bitacora(campos, bitacora_id=bitacora_id)
            st.success(f"Bitácora N° {nro} guardada.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")


with tab_nueva:
    if not puede_mant:
        st.warning("Tu rol no puede cargar bitácoras de mantenimiento.")
    else:
        _form_bitacora(veh)

with tab_hist:
    bits = db.bitacoras_de_vehiculo(veh["id"])
    if not bits:
        st.info("Este móvil no tiene bitácoras cargadas.")
    else:
        for b in bits:
            with st.expander(
                f"N° {b['nro_bitacora']} · {b['fecha_bitacora']} · "
                f"{ESTADO_LABEL.get(b['estado'], b['estado'])} · {b.get('clase') or '-'}"):
                st.markdown(f"**Elemento:** {b.get('descripcion_elemento') or '-'}")
                st.markdown(f"**Técnico:** {b.get('tecnico_nombre') or '-'} · "
                            f"**Proveedor:** {b.get('proveedor') or '-'} · "
                            f"**Costo:** {b.get('costo') or '-'}")
                st.markdown(f"**Se observa:** {b.get('se_observa') or '-'}")
                st.markdown(f"**Acciones:** {b.get('acciones') or '-'}")
                st.markdown(f"**Observaciones:** {b.get('observaciones') or '-'}")
                if puede_mant:
                    if st.checkbox("✏️ Editar esta bitácora", key=f"edit_{b['id']}"):
                        _form_bitacora(veh, datos=b, bitacora_id=b["id"])
