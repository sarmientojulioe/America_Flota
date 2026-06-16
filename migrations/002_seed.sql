-- =====================================================
-- Migración 002: Datos iniciales (grupos + catálogo base)
-- Ajustar pesos según criterio de cada responsable
-- =====================================================

INSERT INTO flota.grupos_control (nombre, rol_responsable, aplica_ambulancia, aplica_general, orden) VALUES
('Documentación',   'jefe_flota',   TRUE,  TRUE,  1),
('Mecánica',        'mecanico',     TRUE,  FALSE, 2),
('Equipos Médicos', 'bioingeniero', TRUE,  FALSE, 3),
('Bolso de Trauma', 'enfermero',    TRUE,  FALSE, 4),
('Medicamentos',    'enfermero',    TRUE,  FALSE, 5);

-- ---------- Documentación (todos los vehículos) ----------
INSERT INTO flota.items_catalogo (grupo_id, nombre, tipo, peso, dias_alerta, critico) VALUES
(1, 'VTV / RTO',                  'vencimiento', 100, 30, TRUE),
(1, 'Seguro',                     'vencimiento', 100, 15, TRUE),
(1, 'Cédula verde / Título',      'vencimiento',  20, 60, FALSE),
(1, 'RUTA',                       'vencimiento',  30, 30, FALSE),
(1, 'Habilitación municipal',     'vencimiento',  50, 30, FALSE),
(1, 'Matafuego',                  'vencimiento',  40, 30, FALSE),
(1, 'Botiquín reglamentario',     'checklist',    10, NULL, FALSE),
(1, 'Balizas',                    'checklist',    10, NULL, FALSE);

-- ---------- Mecánica (ambulancias) ----------
INSERT INTO flota.items_catalogo (grupo_id, nombre, tipo, peso, critico) VALUES
(2, 'Frenos',                     'checklist', 100, TRUE),
(2, 'Dirección',                  'checklist', 100, TRUE),
(2, 'Luces reglamentarias',       'checklist',  30, FALSE),
(2, 'Sirena',                     'checklist',  50, TRUE),
(2, 'Balizas de emergencia',      'checklist',  50, TRUE),
(2, 'Niveles de fluidos',         'checklist',  20, FALSE),
(2, 'Neumáticos',                 'checklist',  40, FALSE),
(2, 'Rueda de auxilio',           'checklist',  15, FALSE),
(2, 'Batería',                    'checklist',  30, FALSE),
(2, 'Climatización habitáculo sanitario', 'checklist', 20, FALSE);

-- ---------- Equipos Médicos (bioingeniero) ----------
INSERT INTO flota.items_catalogo (grupo_id, nombre, tipo, peso, dias_alerta, critico) VALUES
(3, 'DEA / Desfibrilador',        'checklist',   100, NULL, TRUE),
(3, 'Tubo de oxígeno principal',  'checklist',   100, NULL, TRUE),
(3, 'Tubo de oxígeno portátil',   'checklist',    50, NULL, TRUE),
(3, 'Aspirador de secreciones',   'checklist',    50, NULL, TRUE),
(3, 'Oxímetro de pulso',          'checklist',    30, NULL, FALSE),
(3, 'Tensiómetro',                'checklist',    30, NULL, FALSE),
(3, 'Camilla principal',          'checklist',   100, NULL, TRUE),
(3, 'Tabla espinal + inmovilizadores', 'checklist', 50, NULL, TRUE),
(3, 'Calibración DEA',            'vencimiento',  60, 60, TRUE),
(3, 'Prueba hidráulica tubos O2', 'vencimiento',  60, 90, TRUE);

-- ---------- Bolso de Trauma (enfermeros) ----------
INSERT INTO flota.items_catalogo (grupo_id, nombre, tipo, peso, cantidad_minima, unidad, critico) VALUES
(4, 'Gasas estériles',            'stock',  5, 20, 'unidades', FALSE),
(4, 'Vendas',                     'stock',  5, 10, 'unidades', FALSE),
(4, 'Guantes descartables',       'stock', 10, 20, 'pares',    FALSE),
(4, 'Collar cervical',            'stock', 30,  2, 'unidades', TRUE),
(4, 'Férulas inflables',          'stock', 20,  2, 'sets',     FALSE),
(4, 'Solución fisiológica',       'stock', 15,  4, 'sachets',  FALSE),
(4, 'Guías de suero',             'stock', 15,  4, 'unidades', FALSE),
(4, 'Catéteres IV (varios calibres)', 'stock', 20, 10, 'unidades', TRUE),
(4, 'Tijera de trauma',           'stock', 10,  1, 'unidades', FALSE);

-- ---------- Medicamentos (enfermeros; stock + vencimiento se controla en vehiculo_items.vence_el) ----------
INSERT INTO flota.items_catalogo (grupo_id, nombre, tipo, peso, cantidad_minima, unidad, dias_alerta, critico) VALUES
(5, 'Adrenalina',                 'stock', 50, 5, 'ampollas', 60, TRUE),
(5, 'Atropina',                   'stock', 40, 5, 'ampollas', 60, TRUE),
(5, 'Amiodarona',                 'stock', 40, 3, 'ampollas', 60, TRUE),
(5, 'Diazepam',                   'stock', 30, 3, 'ampollas', 60, TRUE),
(5, 'Dexametasona',               'stock', 20, 3, 'ampollas', 60, FALSE),
(5, 'Glucosa hipertónica',        'stock', 25, 2, 'ampollas', 60, FALSE),
(5, 'Salbutamol aerosol',         'stock', 20, 1, 'unidades', 60, FALSE),
(5, 'AAS',                        'stock', 15, 10, 'comprimidos', 90, FALSE);
