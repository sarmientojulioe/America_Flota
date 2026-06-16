"""Generación del PDF de una Bitácora de Mantenimiento (ISO R SR 07).

Usa fpdf2 con fuentes core (latin-1): se sanitizan los textos. Mantiene la
identidad de marca (azul corporativo) y el código de formulario en el pie.
"""
from __future__ import annotations

from fpdf import FPDF

NAVY = (34, 53, 91)      # #22355B
GRAY = (60, 60, 60)      # #3C3C3C
LIGHT = (237, 237, 237)  # #EDEDED
DOC_CODE = "R SR 07 - Rev.04"

ESTADO_LABEL = {"en_proceso": "En proceso", "terminado": "Proceso terminado",
                "en_seguimiento": "En seguimiento"}


def _lat(s) -> str:
    return str(s if s is not None else "").encode("latin-1", "replace").decode("latin-1")


def _money(v) -> str:
    return f"$ {float(v or 0):,.2f}" if v not in (None, "") else "-"


class _PDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, _lat(DOC_CODE), align="L")
        self.cell(0, 5, _lat(f"Página {self.page_no()}/{{nb}}"), align="R")


def generar_pdf_bitacora(b: dict, veh: dict) -> bytes:
    pdf = _PDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.alias_nb_pages()
    pdf.set_margins(12, 12, 12)
    pdf.add_page()

    def seccion(titulo):
        pdf.ln(1)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(0, 6, _lat("  " + titulo), ln=1, fill=True)
        pdf.set_text_color(*GRAY)
        pdf.ln(1)

    def par(l1, v1, l2=None, v2=None):
        # Ancho de etiqueta dinámico para que no se pise con el valor.
        pdf.set_font("helvetica", "B", 8)
        w1 = pdf.get_string_width(_lat(l1 + ":")) + 2
        pdf.cell(w1, 5, _lat(l1 + ":"))
        pdf.set_font("helvetica", "", 8)
        if l2 is not None:
            pdf.cell(max(93 - w1, 20), 5, _lat(v1 if v1 not in (None, "") else "-"))
            pdf.set_font("helvetica", "B", 8)
            w2 = pdf.get_string_width(_lat(l2 + ":")) + 2
            pdf.cell(w2, 5, _lat(l2 + ":"))
            pdf.set_font("helvetica", "", 8); pdf.cell(0, 5, _lat(v2 if v2 not in (None, "") else "-"))
        else:
            pdf.cell(0, 5, _lat(v1 if v1 not in (None, "") else "-"))
        pdf.ln(5)

    def bloque(label, value):
        pdf.set_font("helvetica", "B", 8); pdf.cell(0, 5, _lat(label + ":"), ln=1)
        pdf.set_font("helvetica", "", 8); pdf.set_fill_color(*LIGHT)
        pdf.multi_cell(0, 4.6, _lat(value if value not in (None, "") else "-"), fill=True)
        pdf.ln(1)

    # --- Encabezado ---
    pdf.set_font("helvetica", "B", 15); pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, _lat("BITÁCORA DE MANTENIMIENTO"), align="C", ln=1)
    pdf.set_font("helvetica", "", 9); pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, _lat(f"{veh['dominio']}   ·   Bitácora N° {b['nro_bitacora']}   ·   "
                        f"{ESTADO_LABEL.get(b['estado'], b['estado'])}"), align="C", ln=1)
    pdf.ln(2); pdf.set_fill_color(*NAVY); pdf.rect(12, pdf.get_y(), 186, 1.2, "F"); pdf.ln(4)

    seccion("DATOS GENERALES")
    par("Fecha bitácora", str(b.get("fecha_bitacora") or "-"), "Lugar prestación", b.get("lugar_prestacion"))
    par("N° bitácora", str(b.get("nro_bitacora")), "Estado", ESTADO_LABEL.get(b.get("estado"), b.get("estado")))

    seccion("TÉCNICO ENCARGADO")
    par("Nombre", b.get("tecnico_nombre"), "Teléfono", b.get("tecnico_telefono"))
    par("Pertenece a", b.get("tecnico_pertenece"))

    seccion("DESCRIPCIÓN DEL EQUIPO")
    par("Móvil / Dominio", veh["dominio"], "Marca / Modelo",
        f"{veh.get('marca') or ''} {veh.get('modelo') or ''}".strip())
    bloque("Descripción detallada del elemento", b.get("descripcion_elemento"))
    par("Validación", b.get("validacion"))

    seccion("TIEMPOS")
    par("Fecha de parada", str(b.get("fecha_parada") or "-"), "Total en hs.", b.get("total_hs"))
    par("Hora inicio", b.get("hora_inicio"), "Hora finalización", b.get("hora_fin"))
    par("Parada", b.get("parada"), "Comienzo de la acción", b.get("comienzo_accion"))
    par("Gestión de abastecimiento", b.get("gestion_abastecimiento"))

    seccion("CLASIFICACIÓN")
    par("Naturaleza", b.get("naturaleza"), "Clase", b.get("clase"))
    par("Tipo de mantenimiento", b.get("tipo_mantenimiento"))

    seccion("COSTOS")
    par("Costo", _money(b.get("costo")), "Proveedor", b.get("proveedor"))

    seccion("DETALLE")
    bloque("Se observa", b.get("se_observa"))
    bloque("Acciones", b.get("acciones"))
    bloque("Observaciones", b.get("observaciones"))
    par("Validación / Autorización", b.get("validacion_autorizacion"))

    pdf.ln(8)
    pdf.set_font("helvetica", "", 9)
    pdf.cell(0, 5, _lat("Firma: __________________________     "
                        "Aclaración: __________________________"), ln=1)

    return bytes(pdf.output())
