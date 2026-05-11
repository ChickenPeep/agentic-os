# Dashboard Phase 2 — Pre-Build Research

> Last updated: 2026-05-10. Sources: nextjs.org/docs (v16.2.6, last updated 2026-05-07), Next.js blog, Cloudflare docs.

---

## 1. Recommended Package Versions

| Package | Recommended version | Notes |
|---|---|---|
| **next** | `16.2.6` | Latest stable as of 2026-05-10. Shipped with Turbopack stable, React Compiler stable, PPR. |
| **react / react-dom** | `19.x` | React 19 became stable with Next.js 15.1 (Dec 2024). Next 16 requires it. |
| **typescript** | `5.x` | Default in `create-next-app`. |
| **@supabase/supabase-js** | `2.x` latest | `npm install @supabase/supabase-js@latest`. |
| **tailwindcss** | `4.x` | Tailwind v4 shipped early 2025. CSS-first config (`@import "tailwindcss"` instead of `tailwind.config.js`). `create-next-app` scaffolds Tailwind by default. |
| **shadcn/ui** | CLI-based, no version pin | `npx shadcn@latest init`. Components copy into your repo. Requires React 19 + Tailwind 4 for latest. |
| **@cloudflare/next-on-pages** | `1.x` latest | **Verify Next.js 16 compat at install time.** |

**Compat warnings:**
- Tailwind v4 is breaking from v3. The `tailwind.config.js` pattern is gone; config is in CSS now.
- React 19 + Next 16 is the correct pairing. Don't mix React 18 with Next 16.
- `create-next-app@latest` defaults to Turbopack (`next dev --turbopack`) — stable.

---

## 2. Cloudflare Pages + Next.js App Router Gotchas

### Adapter situation in 2026

Next.js 16 introduced a stable Adapter API. As of 2026-05-07:
- **Vercel** and **Bun** are the only verified adapters.
- **Cloudflare is building a verified adapter** but it isn't shipped. Until then, **`@cloudflare/next-on-pages`** is the recommended path.

### What `@cloudflare/next-on-pages` does

Transforms the Next.js build output so every route runs as a **Cloudflare Worker** using the **Edge Runtime** (subset of Node.js APIs). Pages deploys to Cloudflare's global edge.

### What works
- Static pages, static exports — full support
- Server Components — work; streaming requires no buffering (Workers support chunked transfer)
- Server Actions — work
- Middleware — works
- Route Handlers (API routes) — work
- `next/image` with `unoptimized: true` — works (default `sharp`-based image optimization does NOT work)

### What breaks or is constrained

| Feature | Status | Workaround |
|---|---|---|
| **Image Optimization** (`next/image` default) | Broken — `sharp` is a native Node module | `images: { unoptimized: true }` in `next.config.js` |
| **ISR** | Per-instance cache only (no shared) | Fine for single-user dashboard |
| **`after()`** | Behavior unclear on Workers | Avoid in this project |
| **Node.js native modules** | Unavailable in Edge Runtime | Use Web-compatible alternatives only |
| **`output: "standalone"`** | Incompatible with `@cloudflare/next-on-pages` | Don't set it |
| **PPR** | Unverified on Cloudflare | Treat as experimental on Pages |

### The "edge runtime" requirement

Every server-side route MUST opt in:
```ts
export const runtime = 'edge'
```
Routes without this that use server features may fail silently or fall back to static. **#1 gotcha.** No project-wide `next.config.ts` setting honored by `@cloudflare/next-on-pages` — must be per-file.

### Build settings

- **Build command:** `npx @cloudflare/next-on-pages`
- **Output directory:** `.vercel/output/static`

### `wrangler.toml` (project root)

```toml
name = "agentic-os-dashboard"
compatibility_date = "2024-09-23"
compatibility_flags = ["nodejs_compat"]
pages_build_output_dir = ".vercel/output/static"
```
The `nodejs_compat` flag enables enough Node APIs for Supabase JS to work.

---

## 3. Supabase Auth Posture for a Single-User Dashboard

**Short answer: anon key with permissive RLS policies. No login UI needed.**

### Recommended setup

1. Keep RLS enabled (good habit; the schema view `status_counts` runs as definer rights anyway).
2. Permissive read policies for anon:
   ```sql
   create policy "anon read" on skills        for select using (true);
   create policy "anon read" on runs          for select using (true);
   create policy "anon read" on plans         for select using (true);
   create policy "anon read" on wiki_articles for select using (true);
   ```
3. **No anon write access.** Inserts to `runs` happen server-side from the n8n workflow (using service role key).
4. Optional: lock the entire dashboard behind **Cloudflare Access** (free, uses your Google account, invisible to app code) — recommended once domain is live.

### Env vars

```
NEXT_PUBLIC_SUPABASE_URL=https://ykfjnageewaonunrnwft.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

`NEXT_PUBLIC_` prefix → exposed to client bundle. Safe with RLS.

---

## 4. GitHub → Cloudflare Pages Auto-Deploy Setup

Click path (2026 dashboard):

1. dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** tab → **Connect to Git**
2. Authorize GitHub → select repo `ChickenPeep/agentic-os`
3. **Project name:** `agentic-os-dashboard` → becomes `agentic-os-dashboard.pages.dev`
4. **Production branch:** `main`
5. **Framework preset:** Next.js. Verify build settings:
   - **Build command:** `npx @cloudflare/next-on-pages`
   - **Build output directory:** `.vercel/output/static`
   - **Root directory:** `agentic-os/dashboard` (since the repo root is the vault, not the Next.js app)
6. **Environment variables:**

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://ykfjnageewaonunrnwft.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<anon key>` |
| `NODE_VERSION` | `20` |

7. Save and Deploy. Every push to `main` triggers a deploy. PRs get preview URLs.

**Critical:** because the Next.js app is at `agentic-os/dashboard/` (not repo root), set **Root directory** to that path. If the field is missing in the UI, prefix the build command: `cd agentic-os/dashboard && npx @cloudflare/next-on-pages`.

---

## 5. Recommended Folder Structure

```
agentic-os/dashboard/           ← Next.js project root (Cloudflare Pages "Root directory")
├── wrangler.toml               ← Cloudflare Workers/Pages config
├── next.config.ts              ← images.unoptimized: true
├── package.json
├── tsconfig.json
├── .env.local                  ← Local dev only, gitignored
│
├── app/                        ← Next.js App Router
│   ├── layout.tsx              ← Root layout (fonts, global styles)
│   ├── page.tsx                ← Dashboard home — 7-column board
│   ├── globals.css             ← Tailwind @import + tokens
│   │
│   ├── api/
│   │   └── run/route.ts        ← Proxy "Run" button → webhook (server-side, hides URL)
│   │
│   └── components/
│       ├── SkillCard.tsx
│       ├── DomainColumn.tsx
│       ├── RunHistory.tsx
│       ├── PlanCapture.tsx
│       └── StatusHeader.tsx
│
├── lib/
│   ├── supabase.ts             ← createClient() singleton
│   └── types.ts                ← DB types (Skill, Run, Plan, WikiArticle)
│
└── public/                     ← Static assets
```

Notes:
- No `src/` wrapper — flat for a small project
- `app/api/run/route.ts` has `export const runtime = 'edge'`, proxies POST to webhook (URL = env var, can change without redeploy)
- Every `app/` file doing server work needs `export const runtime = 'edge'`

---

## 6. UI Library — Tailwind v4 + shadcn/ui (recommended)

7-column layout: `grid grid-cols-7 gap-4` with each column holding shadcn `Card` components.

Why shadcn:
- Components copy into your repo — no version lock-in
- Plays with Tailwind v4 + React 19
- Card, Badge, Button, Dialog, Textarea cover the entire dashboard

Risk: if Tailwind v4 + shadcn install path is rough at scaffold time, fall back to plain Tailwind utilities (option B).

---

## 7. Open Questions / Risks Before Scaffolding

1. **`@cloudflare/next-on-pages` × Next.js 16 compat** — verify with `npm info @cloudflare/next-on-pages peerDependencies` BEFORE `create-next-app`. If incompatible, pin to Next.js 15.x.
2. **Cloudflare Access** — strong recommendation to gate the Pages domain behind Zero Trust before any real data lands there. 5-min setup once domain is live.
3. **Stable webhook URL timing** — the temporary trycloudflare URL changes on cloudflared restart. Route the "Run" button POST through `app/api/run/route.ts` (server-side env var) so the URL can change without a deploy.
4. **`status_counts` view + RLS** — views in Postgres run with definer rights, no RLS inheritance. Verify accessible via anon key after deploy.
5. **shadcn × Tailwind v4 install flow** — `npx shadcn@latest init` should detect v4. Don't follow tutorials showing `tailwind.config.js`.

---

## Top 3 Surprises

1. **Next.js is at 16.2.6, not 14.** The plan referenced "Next.js 14" — App Router mental model is the same, but use 16.
2. **Cloudflare's verified adapter is still not shipped.** `@cloudflare/next-on-pages` is the path; it has historically lagged Next.js majors.
3. **Every server route needs `export const runtime = 'edge'`.** Easy to forget; silently breaks routes on Cloudflare Pages.

## Blocking unknowns for the user

- **Verify `@cloudflare/next-on-pages` works with Next.js 16** before scaffolding
- **Decide on Cloudflare Access** (recommended yes — gate the Pages domain behind Google login)

---

**Sources:** nextjs.org/docs (Deploying, Self-Hosting, Adapters, create-next-app, adapterPath), nextjs.org/blog
