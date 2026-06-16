# FlotaApp — Control de Flota y Disponibilidad
American Advisor · Mesa Operativa

## Concepto
Cada vehículo tiene grupos de control con ítems ponderados. La disponibilidad se calcula en PostgreSQL (trigger):
- Disponibilidad = 100 − Σ peso (ítems vencidos/faltantes) − Σ peso/2 (ítems en alerta)
- ≥90% Operativo · 60–89% Operativo c/ observaciones · <60% Fuera de servicio
- Mesa operativa puede aplicar override manual con motivo.

## Roles
| Rol | Grupo |
|---|---|
| jefe_flota | Documentación (toda la flota) |
| mecanico | Mecánica (ambulancias) |
| bioingeniero | Equipos Médicos |
| enfermero | Bolso de Trauma + Medicamentos |
| resp_mesa_operativa | Todo + override |

## Setup
1. En Supabase SQL Editor, ejecutar `migrations/001_schema.sql` y luego `002_seed.sql`.
2. Crear usuarios en Supabase Auth y luego insertar su perfil:
   ```sql
   INSERT INTO perfiles (id, nombre, rol) VALUES ('<uuid-auth>', 'Nombre', 'mecanico');
   ```
3. Copiar `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` y completar credenciales.
4. `pip install -r requirements.txt && streamlit run app.py`

## Integración n8n
La vista `v_vencimientos` expone dominio, ítem, fecha y días restantes — conectar igual que las alertas de inspecciones/calibraciones.
