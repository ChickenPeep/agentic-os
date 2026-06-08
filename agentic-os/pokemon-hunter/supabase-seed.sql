-- POKEMON domain skill rows for the agentic-os dashboard.
-- Apply once (Supabase SQL editor or MCP). After applying, copy the check-stock
-- row's id into ~/.agentic-os.env as POKEMON_CHECK_STOCK_SKILL_ID so run.sh can log runs.

insert into skills (domain, name, slug, description, type, status, host)
values
  ('POKEMON', 'check-stock', 'pokemon.check-stock',
   'Polls Target/Best Buy/Walmart/Sams for in-stock Pokemon sealed product at WI stores; Discord-alerts on rising edge.',
   'routine', 'active', 'mac'),
  ('POKEMON', 'research-drops', 'pokemon.research-drops',
   'Weekly: researches upcoming Pokemon sealed release dates into a wiki camping calendar.',
   'routine', 'active', 'mac')
on conflict (slug) do update
  set description = excluded.description,
      domain = excluded.domain,
      type = excluded.type,
      host = excluded.host;

-- Get the id to put in the env:
-- select id, slug from skills where slug = 'pokemon.check-stock';
