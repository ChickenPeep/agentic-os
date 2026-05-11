export const runtime = 'edge';

/**
 * POST /api/run
 * Body: { skill_slug: string }
 *
 * Phase 2.1: fire-and-forget pattern.
 *   1. Fetch skill row from Supabase (including prompt) using service role key.
 *   2. Insert a runs row with status='running', get back the run_id.
 *   3. Fire the n8n webhook with prompt + skill_slug + run_id — do NOT await.
 *   4. Return { run_id, status: "queued", skill_slug } immediately.
 *
 * Client polls /api/run/[run_id] every 2s until status is success or failure.
 * n8n workflow is responsible for updating the runs row when complete.
 *
 * Server-side env vars (NOT NEXT_PUBLIC_): SUPABASE_SERVICE_ROLE_KEY
 * Public env vars: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_RUN_WEBHOOK_URL
 */

export async function POST(request: Request) {
  let body: { skill_slug?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { skill_slug } = body;
  if (!skill_slug) {
    return Response.json({ error: 'skill_slug required' }, { status: 400 });
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const webhookUrl = process.env.NEXT_PUBLIC_RUN_WEBHOOK_URL;

  if (!supabaseUrl || !serviceRoleKey) {
    return Response.json({ error: 'Supabase not configured' }, { status: 500 });
  }
  if (!webhookUrl) {
    return Response.json({ error: 'Webhook not configured' }, { status: 500 });
  }

  // 1. Fetch skill row including prompt (service role bypasses RLS)
  const skillRes = await fetch(
    `${supabaseUrl}/rest/v1/skills?slug=eq.${encodeURIComponent(skill_slug)}&select=id,slug,name,status,prompt&limit=1`,
    {
      headers: {
        apikey: serviceRoleKey,
        Authorization: `Bearer ${serviceRoleKey}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (!skillRes.ok) {
    return Response.json({ error: 'Failed to fetch skill' }, { status: 502 });
  }

  const skills: Array<{
    id: string;
    slug: string;
    name: string;
    status: string;
    prompt: string | null;
  }> = await skillRes.json();

  if (!skills.length) {
    return Response.json({ error: `Skill not found: ${skill_slug}` }, { status: 404 });
  }

  const skill = skills[0];

  if (skill.status !== 'active') {
    return Response.json(
      { error: 'Skill is not active', status: skill.status, skill_slug },
      { status: 422 }
    );
  }

  const prompt =
    skill.prompt ?? `Execute skill ${skill_slug}`;

  // 2. Insert a runs row with status='running', capture id
  const runInsertRes = await fetch(
    `${supabaseUrl}/rest/v1/runs`,
    {
      method: 'POST',
      headers: {
        apikey: serviceRoleKey,
        Authorization: `Bearer ${serviceRoleKey}`,
        'Content-Type': 'application/json',
        Prefer: 'return=representation',
      },
      body: JSON.stringify({
        skill_id: skill.id,
        started_at: new Date().toISOString(),
        status: 'running',
        triggered_by: 'dashboard',
        host: 'mac',
      }),
    }
  );

  if (!runInsertRes.ok) {
    const errText = await runInsertRes.text();
    return Response.json({ error: `Failed to insert run: ${errText}` }, { status: 502 });
  }

  const runRows: Array<{ id: string }> = await runInsertRes.json();
  const run_id = runRows[0]?.id;

  if (!run_id) {
    return Response.json({ error: 'Failed to get run_id from insert' }, { status: 500 });
  }

  // 3. Fire-and-forget: POST to n8n webhook — do NOT await
  // Using void to explicitly discard the promise (no await = no edge timeout concern)
  void fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      skill_slug,
      prompt,
      triggered_by: 'dashboard',
      run_id,
    }),
  }).catch(() => {
    // Silently discard webhook errors — n8n will update status when/if it completes
  });

  // 4. Return immediately
  return Response.json({ run_id, status: 'queued', skill_slug });
}
