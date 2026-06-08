-- COMMAND-CENTER bot skill row for the dashboard.
-- After applying: select id from skills where slug = 'command-center.bot';
-- and put it in ~/.agentic-os.env as COMMAND_CENTER_BOT_SKILL_ID.
insert into skills (domain, name, slug, description, type, status, host)
values
  ('COMMAND-CENTER', 'bot', 'command-center.bot',
   'Discord bot bridging Gabe''s phone to Claude Code on the Mac mini; logs ideas and staged work.',
   'agent', 'active', 'mac')
on conflict (slug) do update
  set description = excluded.description,
      domain = excluded.domain,
      type = excluded.type,
      host = excluded.host;
