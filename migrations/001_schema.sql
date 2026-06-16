-- =====================================================
-- FlotaApp - Control de Flota y Disponibilidad
-- American Advisor - Mesa Operativa
-- Migración 001: Esquema base
-- Schema dedicado "flota" (instancia compartida con proyecto cotizaciones)
-- =====================================================

CREATE SCHEMA IF NOT EXISTS flota;

-- ---------- ENUMS ----------
CREATE TYPE flota.tipo_vehiculo AS ENUM ('ambulancia', 'utilitario', 'camioneta', 'auto', 'camion', 'otro');
CREATE TYPE flota.tipo_control_item AS ENUM ('vencimiento', 'stock', 'checklist');
CREATE TYPE flota.estado_item AS ENUM ('ok', 'alerta', 'faltante', 'vencido');
CREATE TYPE flota.rol_usuario AS ENUM ('superadmin', 'resp_mesa_operativa', 'jefe_flota', 'mecanico', 'enfermero', 'bioingeniero');
CREATE TYPE flota.estado_vehiculo AS ENUM ('operativo', 'operativo_obs', 'fuera_servicio');

-- ---------- USUARIOS ----------
CREATE TABLE flota.perfiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    rol flota.rol_usuario NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- VEHÍCULOS ----------
CREATE TABLE flota.vehiculos (
    id BIGSERIAL PRIMARY KEY,
    dominio TEXT NOT NULL UNIQUE,
    tipo flota.tipo_vehiculo NOT NULL,
    marca TEXT,
    modelo TEXT,
    anio INT,
    interno TEXT,                          -- número interno de flota
    disponibilidad NUMERIC(5,2) NOT NULL DEFAULT 100,   -- calculada por trigger
    estado flota.estado_vehiculo NOT NULL DEFAULT 'operativo', -- calculado por trigger
    estado_manual flota.estado_vehiculo,   -- override de mesa operativa (NULL = automático)
    motivo_override TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- GRUPOS DE CONTROL ----------
CREATE TABLE flota.grupos_control (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    rol_responsable flota.rol_usuario NOT NULL,
    aplica_ambulancia BOOLEAN NOT NULL DEFAULT TRUE,
    aplica_general BOOLEAN NOT NULL DEFAULT FALSE,  -- aplica a vehículos no-ambulancia
    orden INT NOT NULL DEFAULT 0
);

-- ---------- CATÁLOGO DE ÍTEMS ----------
CREATE TABLE flota.items_catalogo (
    id BIGSERIAL PRIMARY KEY,
    grupo_id BIGINT NOT NULL REFERENCES flota.grupos_control(id),
    nombre TEXT NOT NULL,
    tipo flota.tipo_control_item NOT NULL,
    peso NUMERIC(5,2) NOT NULL DEFAULT 5,   -- impacto sobre disponibilidad (0-100)
    dias_alerta INT DEFAULT 30,             -- para tipo vencimiento: alerta anticipada
    cantidad_minima NUMERIC DEFAULT NULL,   -- para tipo stock
    unidad TEXT,                            -- ej: unidades, ampollas, litros
    critico BOOLEAN NOT NULL DEFAULT FALSE, -- crítico => peso aplicado completo y resaltado
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (grupo_id, nombre)
);

-- ---------- ÍTEMS POR VEHÍCULO (estado actual) ----------
CREATE TABLE flota.vehiculo_items (
    id BIGSERIAL PRIMARY KEY,
    vehiculo_id BIGINT NOT NULL REFERENCES flota.vehiculos(id) ON DELETE CASCADE,
    item_id BIGINT NOT NULL REFERENCES flota.items_catalogo(id),
    vence_el DATE,                 -- tipo vencimiento
    cantidad_actual NUMERIC,       -- tipo stock
    estado flota.estado_item NOT NULL DEFAULT 'ok',
    observacion TEXT,
    actualizado_por UUID REFERENCES flota.perfiles(id),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vehiculo_id, item_id)
);

-- ---------- CONTROLES (auditoría) ----------
CREATE TABLE flota.controles (
    id BIGSERIAL PRIMARY KEY,
    vehiculo_id BIGINT NOT NULL REFERENCES flota.vehiculos(id),
    grupo_id BIGINT NOT NULL REFERENCES flota.grupos_control(id),
    usuario_id UUID NOT NULL REFERENCES flota.perfiles(id),
    fecha TIMESTAMPTZ NOT NULL DEFAULT now(),
    observaciones TEXT
);

CREATE TABLE flota.controles_detalle (
    id BIGSERIAL PRIMARY KEY,
    control_id BIGINT NOT NULL REFERENCES flota.controles(id) ON DELETE CASCADE,
    item_id BIGINT NOT NULL REFERENCES flota.items_catalogo(id),
    estado flota.estado_item NOT NULL,
    cantidad_registrada NUMERIC,
    vence_el DATE,
    observacion TEXT,
    foto_url TEXT
);

-- =====================================================
-- FUNCIÓN: estado efectivo de un ítem
-- =====================================================
CREATE OR REPLACE FUNCTION flota.fn_estado_item(
    p_tipo flota.tipo_control_item,
    p_vence_el DATE,
    p_dias_alerta INT,
    p_cantidad_actual NUMERIC,
    p_cantidad_minima NUMERIC,
    p_estado_manual flota.estado_item
) RETURNS flota.estado_item LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_tipo = 'vencimiento' THEN
        IF p_vence_el IS NULL THEN RETURN 'faltante'; END IF;
        IF p_vence_el < CURRENT_DATE THEN RETURN 'vencido'; END IF;
        IF p_vence_el <= CURRENT_DATE + COALESCE(p_dias_alerta, 30) THEN RETURN 'alerta'; END IF;
        RETURN 'ok';
    ELSIF p_tipo = 'stock' THEN
        IF p_cantidad_actual IS NULL OR p_cantidad_actual <= 0 THEN RETURN 'faltante'; END IF;
        IF p_cantidad_minima IS NOT NULL AND p_cantidad_actual < p_cantidad_minima THEN RETURN 'alerta'; END IF;
        RETURN 'ok';
    ELSE -- checklist
        RETURN COALESCE(p_estado_manual, 'ok');
    END IF;
END $$;

-- =====================================================
-- FUNCIÓN + TRIGGER: recálculo de disponibilidad
-- Disponibilidad = 100 - SUM(peso de ítems vencidos/faltantes)
--                  - SUM(peso/2 de ítems en alerta)
-- =====================================================
CREATE OR REPLACE FUNCTION flota.fn_recalcular_disponibilidad(p_vehiculo_id BIGINT)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    v_descuento NUMERIC := 0;
    v_disp NUMERIC;
    v_estado flota.estado_vehiculo;
BEGIN
    SELECT COALESCE(SUM(
        CASE vi.estado
            WHEN 'vencido'  THEN ic.peso
            WHEN 'faltante' THEN ic.peso
            WHEN 'alerta'   THEN ic.peso / 2.0
            ELSE 0
        END), 0)
    INTO v_descuento
    FROM flota.vehiculo_items vi
    JOIN flota.items_catalogo ic ON ic.id = vi.item_id
    WHERE vi.vehiculo_id = p_vehiculo_id AND ic.activo;

    v_disp := GREATEST(0, 100 - v_descuento);

    v_estado := CASE
        WHEN v_disp >= 90 THEN 'operativo'::flota.estado_vehiculo
        WHEN v_disp >= 60 THEN 'operativo_obs'::flota.estado_vehiculo
        ELSE 'fuera_servicio'::flota.estado_vehiculo
    END;

    UPDATE flota.vehiculos
    SET disponibilidad = v_disp,
        estado = v_estado
    WHERE id = p_vehiculo_id;
END $$;

CREATE OR REPLACE FUNCTION flota.trg_vehiculo_items_recalc()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    PERFORM flota.fn_recalcular_disponibilidad(COALESCE(NEW.vehiculo_id, OLD.vehiculo_id));
    RETURN COALESCE(NEW, OLD);
END $$;

CREATE TRIGGER t_recalc_disponibilidad
AFTER INSERT OR UPDATE OR DELETE ON flota.vehiculo_items
FOR EACH ROW EXECUTE FUNCTION flota.trg_vehiculo_items_recalc();

-- =====================================================
-- VISTA: estado de flota para dashboard
-- =====================================================
CREATE OR REPLACE VIEW flota.v_flota_estado AS
SELECT
    v.id, v.dominio, v.interno, v.tipo, v.marca, v.modelo,
    v.disponibilidad,
    COALESCE(v.estado_manual, v.estado) AS estado_efectivo,
    v.estado_manual IS NOT NULL AS tiene_override,
    v.motivo_override,
    (SELECT COUNT(*) FROM flota.vehiculo_items vi JOIN flota.items_catalogo ic ON ic.id = vi.item_id
     WHERE vi.vehiculo_id = v.id AND vi.estado IN ('vencido','faltante')) AS items_criticos,
    (SELECT COUNT(*) FROM flota.vehiculo_items vi
     WHERE vi.vehiculo_id = v.id AND vi.estado = 'alerta') AS items_alerta,
    (SELECT MIN(vi.vence_el) FROM flota.vehiculo_items vi JOIN flota.items_catalogo ic ON ic.id = vi.item_id
     WHERE vi.vehiculo_id = v.id AND ic.tipo = 'vencimiento' AND vi.vence_el >= CURRENT_DATE) AS proximo_vencimiento
FROM flota.vehiculos v
WHERE v.activo;

-- =====================================================
-- VISTA: vencimientos próximos (para n8n / alertas)
-- =====================================================
CREATE OR REPLACE VIEW flota.v_vencimientos AS
SELECT
    v.dominio, v.interno, v.tipo AS tipo_vehiculo,
    g.nombre AS grupo, ic.nombre AS item,
    vi.vence_el,
    vi.vence_el - CURRENT_DATE AS dias_restantes,
    vi.estado
FROM flota.vehiculo_items vi
JOIN flota.vehiculos v ON v.id = vi.vehiculo_id AND v.activo
JOIN flota.items_catalogo ic ON ic.id = vi.item_id AND ic.tipo = 'vencimiento'
JOIN flota.grupos_control g ON g.id = ic.grupo_id
WHERE vi.vence_el IS NOT NULL
ORDER BY vi.vence_el;

-- =====================================================
-- GRANTS: exponer schema flota a los roles de PostgREST
-- (RLS sigue restringiendo el acceso por fila)
-- =====================================================
GRANT USAGE ON SCHEMA flota TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES    IN SCHEMA flota TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA flota TO anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA flota TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA flota GRANT ALL ON TABLES    TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA flota GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA flota GRANT ALL ON FUNCTIONS TO anon, authenticated, service_role;

-- =====================================================
-- RLS (Row Level Security) - base
-- =====================================================
ALTER TABLE flota.perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE flota.vehiculos ENABLE ROW LEVEL SECURITY;
ALTER TABLE flota.vehiculo_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE flota.controles ENABLE ROW LEVEL SECURITY;
ALTER TABLE flota.controles_detalle ENABLE ROW LEVEL SECURITY;
ALTER TABLE flota.grupos_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE flota.items_catalogo ENABLE ROW LEVEL SECURITY;

-- Lectura para todos los autenticados
CREATE POLICY p_read_all ON flota.vehiculos FOR SELECT TO authenticated USING (true);
CREATE POLICY p_read_all ON flota.vehiculo_items FOR SELECT TO authenticated USING (true);
CREATE POLICY p_read_all ON flota.controles FOR SELECT TO authenticated USING (true);
CREATE POLICY p_read_all ON flota.controles_detalle FOR SELECT TO authenticated USING (true);
CREATE POLICY p_read_all ON flota.grupos_control FOR SELECT TO authenticated USING (true);
CREATE POLICY p_read_all ON flota.items_catalogo FOR SELECT TO authenticated USING (true);
CREATE POLICY p_read_perfil ON flota.perfiles FOR SELECT TO authenticated USING (true);

-- Escritura: cada rol escribe ítems de su grupo
CREATE POLICY p_write_items ON flota.vehiculo_items FOR ALL TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM flota.items_catalogo ic
        JOIN flota.grupos_control g ON g.id = ic.grupo_id
        JOIN flota.perfiles p ON p.id = auth.uid()
        WHERE ic.id = vehiculo_items.item_id
          AND (p.rol = g.rol_responsable OR p.rol IN ('superadmin','resp_mesa_operativa'))
    )
);

CREATE POLICY p_write_controles ON flota.controles FOR INSERT TO authenticated
WITH CHECK (usuario_id = auth.uid());
CREATE POLICY p_write_controles_det ON flota.controles_detalle FOR INSERT TO authenticated WITH CHECK (true);
