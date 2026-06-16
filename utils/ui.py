"""Branding American Advisor - paleta, estilos y componentes UI."""
import base64
from pathlib import Path

import streamlit as st

# Carpeta de recursos de marca (isologos, manual de marca)
ASSETS = Path(__file__).resolve().parent.parent / "assets"
MANUAL_MARCA = ASSETS / "Manual de marca.pdf"

# Certificaciones ISO (archivo, etiqueta accesible)
ISOLOGOS = [
    ("isologo9001.png", "ISO 9001 · Calidad"),
    ("isologo14001.jpg", "ISO 14001 · Ambiente"),
    ("isologo45001.png", "ISO 45001 · Seguridad y Salud"),
]

# Paleta de marca
NAVY = "#22355B"
BLUE_MED = "#2884C7"
BLUE_LIGHT = "#50A5D9"
TEAL = "#3EBAC8"
ORANGE = "#E85C1A"

# Colores semánticos
OK = "#2E9E5B"
WARN = "#E8A21A"
DANGER = "#D9433B"

ESTADO_COLOR = {
    "operativo": OK,
    "operativo_obs": WARN,
    "fuera_servicio": DANGER,
}
ESTADO_LABEL = {
    "operativo": "Operativo",
    "operativo_obs": "Operativo c/ observaciones",
    "fuera_servicio": "Fuera de servicio",
}
ITEM_COLOR = {"ok": OK, "alerta": WARN, "faltante": DANGER, "vencido": DANGER}


def aplicar_estilos():
    # Tema base (claro, paleta corporativa, sidebar gris) vía .streamlit/config.toml,
    # igual que la app Cotizaciones. Acá solo se aplican las tipografías oficiales
    # del Manual de marca (Lato para títulos, Open Sans para textos) y los
    # componentes propios de FlotaApp (badges, tarjetas de vehículo).
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&family=Open+Sans:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Open Sans', sans-serif; }}
    h1, h2, h3 {{ font-family: 'Lato', sans-serif; color: {NAVY}; }}
    .badge {{
        display:inline-block; padding:4px 12px; border-radius:12px;
        color:white; font-weight:600; font-size:0.85rem;
    }}
    .card-vehiculo {{
        border:1px solid #e0e0e0; border-left:6px solid {BLUE_MED};
        border-radius:8px; padding:14px 18px; margin-bottom:10px;
        background:white; box-shadow:0 1px 3px rgba(0,0,0,0.06);
    }}
    </style>
    """, unsafe_allow_html=True)


def _img_data_uri(path: Path) -> str:
    """Devuelve el data URI base64 de una imagen para incrustar en HTML."""
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def isologos(height: int = 48, gap: int = 22) -> str:
    """Tira HTML con los isologos de certificación ISO (embebidos en base64)."""
    imgs = []
    for archivo, alt in ISOLOGOS:
        ruta = ASSETS / archivo
        if not ruta.exists():
            continue
        imgs.append(
            f'<img src="{_img_data_uri(ruta)}" alt="{alt}" title="{alt}" '
            f'style="height:{height}px; width:auto;">'
        )
    if not imgs:
        return ""
    return (f'<div style="display:flex; align-items:center; flex-wrap:wrap; '
            f'gap:{gap}px;">{"".join(imgs)}</div>')


def sidebar_footer():
    """Pie del sidebar con isologos ISO y descarga del manual de marca.

    Pensado para invocarse en páginas autenticadas (vía db.require_login),
    por lo que solo lo ven usuarios logueados.
    """
    tira = isologos(height=34, gap=12)
    if tira:
        st.sidebar.markdown(
            '<div style="margin-top:24px; padding:12px; border-radius:8px; '
            f'background:white;">{tira}</div>',
            unsafe_allow_html=True,
        )
    if MANUAL_MARCA.exists():
        st.sidebar.download_button(
            "📄 Manual de marca",
            data=MANUAL_MARCA.read_bytes(),
            file_name=MANUAL_MARCA.name,
            mime="application/pdf",
            use_container_width=True,
            key="dl_manual_marca",
        )


def badge_estado(estado: str) -> str:
    color = ESTADO_COLOR.get(estado, BLUE_MED)
    label = ESTADO_LABEL.get(estado, estado)
    return f'<span class="badge" style="background:{color}">{label}</span>'


def card_vehiculo(v: dict):
    color = ESTADO_COLOR.get(v["estado_efectivo"], BLUE_MED)
    override = " 🔒 Override manual" if v.get("tiene_override") else ""
    st.markdown(f"""
    <div class="card-vehiculo" style="border-left-color:{color}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <strong style="font-size:1.1rem; color:{NAVY}">{v['dominio']}</strong>
                &nbsp;<span style="color:#777">Int. {v.get('interno') or '-'} · {v['tipo'].title()}</span>
                <span style="color:#999; font-size:0.85rem">{override}</span>
            </div>
            <div style="text-align:right">
                {badge_estado(v['estado_efectivo'])}
                <div style="font-size:1.4rem; font-weight:900; color:{color}">{v['disponibilidad']:.0f}%</div>
            </div>
        </div>
        <div style="margin-top:6px; font-size:0.85rem; color:#666">
            Faltantes/vencidos: <b style="color:{DANGER}">{v['items_criticos']}</b> ·
            Alertas: <b style="color:{WARN}">{v['items_alerta']}</b> ·
            Próx. vencimiento: <b>{v.get('proximo_vencimiento') or '-'}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
