# Agentic OS Dashboard

Next.js 15.5 + Cloudflare Pages + Supabase. Personal control surface for the Agentic OS.

## Local dev

```bash
npm run dev
```

Opens at http://localhost:3000. Reads `.env.local` for Supabase credentials.

## Standard build

```bash
npm run build
```

## Build for Cloudflare Pages

```bash
npm run pages:build
# equivalent: npx @cloudflare/next-on-pages
```

Output lands in `.vercel/output/static/`.

## Connect to Cloudflare Pages (one-time, manual)

1. dash.cloudflare.com -> Workers & Pages -> Create -> Pages -> Connect to Git
2. Authorize GitHub -> select repo `ChickenPeep/agentic-os`
3. Project name: `agentic-os-dashboard`
4. Production branch: `main`
5. Framework preset: Next.js
6. Build command: `npx @cloudflare/next-on-pages`
7. Build output directory: `.vercel/output/static`
8. Root directory: `agentic-os/dashboard`
9. Environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://ykfjnageewaonunrnwft.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = (from credentials/.env)
   - `NODE_VERSION` = `20`
10. Save and Deploy.

Every push to `main` triggers a redeploy. PRs get preview URLs automatically.

## Before first deploy: run RLS policies

Open `RLS-POLICIES.sql` and run it in the Supabase SQL editor:
https://supabase.com/dashboard/project/ykfjnageewaonunrnwft/sql

This lets the anon key read from `skills`, `runs`, `plans`, and `wiki_articles`.

## Stubs (Phase 2.1 work)

The Run button is stubbed. To wire it up:
1. Open `app/api/run/route.ts`
2. Remove the mock return block
3. Uncomment the real fetch call
4. Set `NEXT_PUBLIC_RUN_WEBHOOK_URL` in Cloudflare Pages env vars to your n8n webhook URL

## Architecture

```
app/page.tsx              Server component, fetches skills + runs, renders board
app/api/run/route.ts      Edge route, stub today, proxies to webhook in Phase 2.1
app/components/
  StatusHeader.tsx        Header with active/paused/routine/agent counts
  DomainColumn.tsx        One column per domain (9 total)
  SkillCard.tsx           Client component, name + status + Run button
  RunHistory.tsx          Last 10 runs table
lib/supabase.ts           Supabase client singleton
lib/types.ts              Skill, Run, Plan, WikiArticle interfaces
```
