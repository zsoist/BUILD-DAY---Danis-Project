-- ═══════════════════════════════════════════════════════════════════════════
-- Cerrar Supabase: que la llave pública solo pueda ESCRIBIR, nunca leer ni borrar
-- ═══════════════════════════════════════════════════════════════════════════
--
-- QUÉ SE MIDIÓ (2026-09-22, contra el proyecto real, sin destruir nada):
--
--   tabla            leer   insertar   borrar   filas
--   army_events      sí     sí         sí       1.543
--   sim_calls        sí     sí         sí       2.051
--   sim_encuestas    sí     sí         sí         105
--   profiles         sí     sí         sí           0
--
-- El borrado se comprobó con un filtro que no casa con ninguna fila
-- (`?id=eq.-999999999`): devolvió HTTP 204, o sea que la operación se permite.
--
-- POR QUÉ IMPORTA: la llave `sb_publishable_…` es pública por diseño — va en el
-- código que corre en el navegador y cualquiera puede leerla del repo. Eso no es
-- el fallo. El fallo es que las reglas de fila (RLS) le dejan hacer TODO. Rotar
-- la llave no arregla nada: la nueva también sería pública. Lo que hay que
-- cerrar son los permisos.
--
-- QUÉ NECESITA CADA TABLA DE VERDAD:
--   · army_events   — el enjambre INSERTA telemetría. El visor ya no la lee:
--                     lee /feed.json del servidor local. Solo insertar.
--   · sim_calls     — el simulador INSERTA costos. Nadie los lee desde el
--                     navegador. Solo insertar.
--   · sim_encuestas — el simulador INSERTA preguntas y resultados. Solo insertar.
--   · profiles      — vacía y sin uso. Se cierra del todo.
--
-- Tú sigues viendo todo desde el panel de Supabase, que entra con tu sesión y
-- no pasa por estas reglas.
--
-- CÓMO APLICARLO: panel de Supabase → SQL Editor → pegar → Run.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. RLS encendido en todas. Sin esto las políticas ni se consultan ──────
alter table public.army_events   enable row level security;
alter table public.sim_calls     enable row level security;
alter table public.sim_encuestas enable row level security;
alter table public.profiles      enable row level security;

-- ── 2. Fuera lo que haya. Se reconstruye desde cero para no heredar sorpresas
do $$
declare t text; p text;
begin
  foreach t in array array['army_events','sim_calls','sim_encuestas','profiles'] loop
    for p in select policyname from pg_policies
             where schemaname='public' and tablename=t loop
      execute format('drop policy %I on public.%I', p, t);
    end loop;
  end loop;
end $$;

-- ── 3. Solo insertar, y solo en las tres que lo necesitan ─────────────────
-- Nada de select, update ni delete: lo que no se concede, no existe.
create policy "anon solo inserta" on public.army_events
  for insert to anon with check (true);

create policy "anon solo inserta" on public.sim_calls
  for insert to anon with check (true);

create policy "anon solo inserta" on public.sim_encuestas
  for insert to anon with check (true);

-- profiles no la usa nadie: queda con RLS y sin una sola política, que en
-- Postgres significa "nadie pasa".

-- ── 4. Quitar el permiso de tabla, no solo la política ────────────────────
-- RLS filtra filas, pero el GRANT decide si la orden llega siquiera. Con los
-- dos cerrados, un DELETE ni se intenta.
revoke all on public.army_events, public.sim_calls,
              public.sim_encuestas, public.profiles from anon;
grant insert on public.army_events, public.sim_calls,
                public.sim_encuestas to anon;

-- Las secuencias de los id, para que el insert no falle por eso
grant usage, select on all sequences in schema public to anon;


-- ═══ COMPROBACIÓN ═══════════════════════════════════════════════════════════
-- Debe salir una sola fila por tabla, y solo con INSERT.
select tablename, policyname, cmd, roles
from pg_policies where schemaname='public'
order by tablename;

-- Y esto debe mostrar RLS activo en las cuatro.
select relname as tabla, relrowsecurity as rls_activo
from pg_class where relname in
  ('army_events','sim_calls','sim_encuestas','profiles');


-- ═══ DESPUÉS, DESDE TU TERMINAL ════════════════════════════════════════════
-- Leer debe dar 401; borrar debe dar 401; insertar debe dar 201.
--
--   U=https://<tu-proyecto>.supabase.co
--   K=<tu llave publishable>
--   curl -s -o /dev/null -w "leer    %{http_code}\n" \
--     "$U/rest/v1/army_events?select=*&limit=1" -H "apikey: $K"
--   curl -s -o /dev/null -w "borrar  %{http_code}\n" -X DELETE \
--     "$U/rest/v1/army_events?id=eq.-999999999" -H "apikey: $K"
