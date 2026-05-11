export const runtime = 'edge';

/**
 * GET /api/run/[run_id]
 *
 * Returns the current status + output of a runs row.
 * Client polls this every 2s after calling POST /api/run.
 *
 * Response: { id, status, output, ended_at }
 *   status: 'running' | 'success' | 'failure'
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ run_id: string }> }
) {
  const { run_id } = await params;

  if (!run_id) {
    return Response.json({ error: 'run_id required' }, { status: 400 });
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceRoleKey) {
    return Response.json({ error: 'Supabase not configured' }, { status: 500 });
  }

  const res = await fetch(
    `${supabaseUrl}/rest/v1/runs?id=eq.${encodeURIComponent(run_id)}&select=id,status,output,ended_at&limit=1`,
    {
      headers: {
        apikey: serviceRoleKey,
        Authorization: `Bearer ${serviceRoleKey}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (!res.ok) {
    return Response.json({ error: 'Failed to fetch run' }, { status: 502 });
  }

  const rows: Array<{
    id: string;
    status: string;
    output: string | null;
    ended_at: string | null;
  }> = await res.json();

  if (!rows.length) {
    return Response.json({ error: 'Run not found' }, { status: 404 });
  }

  return Response.json(rows[0]);
}
