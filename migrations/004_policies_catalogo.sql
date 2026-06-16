-- =====================================================
-- Migración 004: Policies de escritura para catálogo y grupos
-- items_catalogo y grupos_control solo tenían SELECT, así que
-- editar el catálogo / crear grupos / mover ítems fallaba con RLS (42501).
-- =====================================================

-- ---- items_catalogo: escribe el responsable del grupo, o mesa operativa / superadmin ----
-- Para MOVER un ítem de grupo, tanto el grupo origen (USING) como el
-- destino (WITH CHECK) deben pasar la verificación.
CREATE POLICY p_write_items_catalogo ON flota.items_catalogo FOR ALL TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM flota.grupos_control g
        JOIN flota.perfiles p ON p.id = auth.uid()
        WHERE g.id = items_catalogo.grupo_id
          AND (p.rol = g.rol_responsable OR p.rol IN ('superadmin', 'resp_mesa_operativa'))
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM flota.grupos_control g
        JOIN flota.perfiles p ON p.id = auth.uid()
        WHERE g.id = items_catalogo.grupo_id
          AND (p.rol = g.rol_responsable OR p.rol IN ('superadmin', 'resp_mesa_operativa'))
    )
);

-- ---- grupos_control: crear/editar grupos solo mesa operativa / superadmin ----
CREATE POLICY p_write_grupos ON flota.grupos_control FOR ALL TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM flota.perfiles p
        WHERE p.id = auth.uid()
          AND p.rol IN ('superadmin', 'resp_mesa_operativa')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM flota.perfiles p
        WHERE p.id = auth.uid()
          AND p.rol IN ('superadmin', 'resp_mesa_operativa')
    )
);
