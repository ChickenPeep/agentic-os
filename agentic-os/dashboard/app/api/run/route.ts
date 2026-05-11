export const runtime = 'edge';

/**
 * POST /api/run
 * Body: { skill_slug: string; prompt?: string }
 *
 * Forwards the request to the n8n webhook at NEXT_PUBLIC_RUN_WEBHOOK_URL.
 *
 * Special case: memory.echo-test always sends a fixed PONG prompt so the
 * dashboard smoke test reliably returns something without a real SKILL.md lookup.
 *
 * Production note: prompt resolution from SKILL.md won't work on Cloudflare
 * Pages (no vault filesystem access). Phase 2.1 should store the canonical
 * prompt in the skills table and read it from there.
 */

export async function POST(request: Request) {
  let body: { skill_slug?: string; prompt?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { skill_slug, prompt } = body;

  if (!skill_slug) {
    return Response.json({ error: 'skill_slug required' }, { status: 400 });
  }

  const webhook = process.env.NEXT_PUBLIC_RUN_WEBHOOK_URL;
  if (!webhook) {
    return Response.json({ error: 'webhook not configured' }, { status: 500 });
  }

  // v1 fallback prompts — replace with skills-table lookup in Phase 2.1
  const resolvedPrompt =
    prompt ||
    (skill_slug === 'memory.echo-test'
      ? 'reply with the literal text PONG and nothing else'
      : `Execute skill ${skill_slug}`);

  let res: Response;
  try {
    res = await fetch(webhook, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skill_slug,
        prompt: resolvedPrompt,
        triggered_by: 'dashboard',
      }),
    });
  } catch (err) {
    return Response.json(
      { error: `Webhook unreachable: ${String(err)}` },
      { status: 502 }
    );
  }

  const text = await res.text();
  let responseBody: unknown;
  try {
    responseBody = JSON.parse(text);
  } catch {
    responseBody = text;
  }

  return Response.json(responseBody, { status: res.status });
}
