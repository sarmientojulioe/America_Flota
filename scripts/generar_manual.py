"""Genera el Manual de Procedimientos en PDF con capturas paso a paso.

Requiere la app corriendo en localhost:8510 y la base lista
(migración 005 aplicada + un vehículo activo).
"""
import os
import time
import pathlib
from playwright.sync_api import sync_playwright
import fitz  # PyMuPDF

URL = os.environ.get("FLOTA_URL", "http://localhost:8510")
# Credenciales por variable de entorno (NO hardcodear en el repo):
#   PowerShell:  $env:FLOTA_EMAIL="..."; $env:FLOTA_PASS="..."; python scripts/generar_manual.py
EMAIL = os.environ.get("FLOTA_EMAIL", "")
PASS = os.environ.get("FLOTA_PASS", "")
if not EMAIL or not PASS:
    raise SystemExit("Faltan credenciales: definí FLOTA_EMAIL y FLOTA_PASS en el entorno.")
OUT = pathlib.Path("scripts/_manual")
OUT.mkdir(parents=True, exist_ok=True)
PDF = pathlib.Path("docs/MANUAL_PROCEDIMIENTOS_FlotaApp.pdf")
PDF.parent.mkdir(parents=True, exist_ok=True)

NAVY = (0.133, 0.208, 0.357)   # #22355B
GRAY = (0.235, 0.235, 0.235)   # #3C3C3C
steps = []  # (img_path, titulo, descripcion)


def shot(page, name, titulo, desc):
    page.wait_for_timeout(1800)
    path = OUT / f"{name}.jpg"
    page.screenshot(path=str(path), full_page=True, type="jpeg", quality=72)
    steps.append((str(path), titulo, desc))
    print("shot:", name)


def nav(page, nombre):
    page.get_by_role("link", name=nombre, exact=True).first.click()
    page.wait_for_timeout(2500)


def tab(page, nombre):
    try:
        page.get_by_role("tab", name=nombre).first.click()
        page.wait_for_timeout(1500)
    except Exception as e:
        print("tab fallo", nombre, e)


def capturar():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1366, "height": 900})
        for _ in range(30):
            try:
                pg.goto(URL, timeout=4000); break
            except Exception:
                time.sleep(1)
        pg.wait_for_load_state("networkidle")

        shot(pg, "01_login", "1. Ingreso al sistema",
             "Abrí la app en el navegador, ingresá tu email y contraseña y presioná "
             "Ingresar. El acceso y los permisos dependen de tu rol.")

        pg.get_by_label("Email").fill(EMAIL)
        pg.get_by_label("Contraseña").fill(PASS)
        pg.get_by_role("button", name="Ingresar").click()
        pg.wait_for_timeout(3000)

        # ---- Vehículos: alta e importación ----
        nav(pg, "Vehiculos")
        tab(pg, "Alta de vehículo")
        shot(pg, "02_veh_alta", "2. Alta de un vehículo",
             "En Vehículos → pestaña 'Alta de vehículo', completá Dominio (obligatorio) "
             "y Tipo. Al crear, el sistema inicializa automáticamente los ítems de control "
             "según el tipo (las ambulancias reciben los 5 grupos).")
        tab(pg, "Importar")
        shot(pg, "03_veh_import", "3. Importación masiva de vehículos",
             "En la pestaña 'Importar' descargá la plantilla Excel, completala y subila. "
             "El sistema previsualiza y valida cada fila (dominio, tipo, duplicados) "
             "antes de confirmar la importación.")

        # ---- Mi Control ----
        nav(pg, "Mi Control")
        shot(pg, "04_micontrol", "4. Carga de un control (Mi Control)",
             "Elegí el Grupo de control y el Vehículo. Cargá cada ítem según su tipo "
             "(fecha de vencimiento, cantidad de stock, o estado de checklist) y presioná "
             "'Registrar control'. La disponibilidad del vehículo se recalcula sola.")

        # ---- Configuración ----
        nav(pg, "Configuracion")
        shot(pg, "05_config", "5. Catálogo, grupos y checklist por vehículo",
             "En Configuración creás grupos de control nuevos, editás pesos, y movés "
             "ítems entre grupos. El checklist propio de cada ambulancia se ajusta desde "
             "Vehículos → 'Personalizar ítems de este vehículo'.")

        # ---- Bitácora ----
        nav(pg, "Bitacora")
        shot(pg, "06_bitacora", "6. Carga de una bitácora de mantenimiento",
             "En Bitácora elegí el móvil y completá la intervención (técnico, elemento, "
             "tiempos, clasificación, costos y observaciones). Cada bitácora queda numerada "
             "y registrada en el historial del móvil.")

        b.close()


def construir_pdf():
    doc = fitz.open()
    # Portada
    portada = doc.new_page(width=595, height=842)
    portada.insert_textbox(fitz.Rect(40, 250, 555, 360),
                           "Manual de Procedimientos\nFlotaApp",
                           fontsize=30, fontname="hebo", color=NAVY, align=1)
    portada.insert_textbox(fitz.Rect(40, 380, 555, 460),
                           "Control de Flota y Disponibilidad\nAmerican Advisor · Mesa Operativa\n\n"
                           "Guía paso a paso de carga de datos",
                           fontsize=13, fontname="helv", color=GRAY, align=1)

    for img_path, titulo, desc in steps:
        page = doc.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(0, 0, 595, 8), color=NAVY, fill=NAVY)
        page.insert_textbox(fitz.Rect(40, 40, 555, 78), titulo,
                            fontsize=16, fontname="hebo", color=NAVY)
        page.insert_textbox(fitz.Rect(40, 80, 555, 150), desc,
                            fontsize=10, fontname="helv", color=GRAY)
        pix = fitz.Pixmap(img_path)
        iw, ih = pix.width, pix.height
        top, margin = 160, 40
        avail_w, avail_h = 595 - 2 * margin, 842 - top - margin
        scale = min(avail_w / iw, avail_h / ih)
        w, h = iw * scale, ih * scale
        x = (595 - w) / 2
        page.insert_image(fitz.Rect(x, top, x + w, top + h), filename=img_path)

    doc.save(str(PDF))
    print("PDF generado:", PDF, "->", len(steps), "pasos")


if __name__ == "__main__":
    capturar()
    construir_pdf()
