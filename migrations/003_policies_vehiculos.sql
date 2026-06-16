-- =====================================================
-- Migración 003: Policy de escritura faltante en vehiculos
-- 001 solo creó la policy de SELECT; el alta/edición de
-- vehículos (mesa operativa / jefe de flota) era bloqueada
-- por RLS (error 42501). Esta policy lo habilita.
-- =====================================================

CREATE POLICY p_write_vehiculos ON flota.vehiculos FOR ALL TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM flota.perfiles p
        WHERE p.id = auth.uid()
          AND p.rol IN ('superadmin', 'resp_mesa_operativa', 'jefe_flota')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM flota.perfiles p
        WHERE p.id = auth.uid()
          AND p.rol IN ('superadmin', 'resp_mesa_operativa', 'jefe_flota')
    )
);
