-- =====================================================
-- Migración 005: Bitácora de Mantenimiento (ISO R SR 07)
-- Registra intervenciones de mantenimiento por móvil.
-- =====================================================

CREATE TYPE flota.estado_bitacora AS ENUM ('en_proceso', 'terminado', 'en_seguimiento');

CREATE TABLE flota.bitacoras (
    id BIGSERIAL PRIMARY KEY,
    vehiculo_id BIGINT NOT NULL REFERENCES flota.vehiculos(id) ON DELETE CASCADE,
    nro_bitacora INT NOT NULL,
    fecha_bitacora DATE NOT NULL DEFAULT CURRENT_DATE,
    lugar_prestacion TEXT,
    -- Técnico encargado
    tecnico_nombre TEXT,
    tecnico_telefono TEXT,
    tecnico_pertenece TEXT,
    -- Equipo / elemento intervenido
    descripcion_elemento TEXT,
    validacion TEXT,
    -- Tiempos
    fecha_parada DATE,
    hora_inicio TEXT,
    hora_fin TEXT,
    total_hs TEXT,
    parada TEXT,
    gestion_abastecimiento TEXT,
    comienzo_accion TEXT,
    -- Clasificación
    naturaleza TEXT,            -- Sanitario / Mecánico
    clase TEXT,                 -- Preventivo / Correctivo / Modificación / Registral
    tipo_mantenimiento TEXT,
    -- Costos
    costo NUMERIC(12,2),
    proveedor TEXT,
    -- Texto libre
    se_observa TEXT,
    acciones TEXT,
    observaciones TEXT,
    validacion_autorizacion TEXT,
    estado flota.estado_bitacora NOT NULL DEFAULT 'en_proceso',
    creado_por UUID REFERENCES flota.perfiles(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vehiculo_id, nro_bitacora)
);

-- Grants (por las dudas, además de los default privileges del schema)
GRANT ALL ON flota.bitacoras TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE flota.bitacoras_id_seq TO anon, authenticated, service_role;

-- RLS
ALTER TABLE flota.bitacoras ENABLE ROW LEVEL SECURITY;

CREATE POLICY p_read_bitacoras ON flota.bitacoras FOR SELECT TO authenticated USING (true);

-- Escribe mantenimiento: jefe de flota, mecánico, o mesa operativa / superadmin
CREATE POLICY p_write_bitacoras ON flota.bitacoras FOR ALL TO authenticated
USING (
    EXISTS (SELECT 1 FROM flota.perfiles p WHERE p.id = auth.uid()
              AND p.rol IN ('superadmin', 'resp_mesa_operativa', 'jefe_flota', 'mecanico'))
)
WITH CHECK (
    EXISTS (SELECT 1 FROM flota.perfiles p WHERE p.id = auth.uid()
              AND p.rol IN ('superadmin', 'resp_mesa_operativa', 'jefe_flota', 'mecanico'))
);
