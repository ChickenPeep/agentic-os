export const runtime = 'edge';

import { supabase } from '@/lib/supabase';
import { Skill, RunWithSkill, StatusCounts, DOMAINS } from '@/lib/types';
import DomainColumn from './components/DomainColumn';
import RunHistory from './components/RunHistory';
import StatusHeader from './components/StatusHeader';

async function fetchData() {
  const [skillsRes, runsRes, countsRes] = await Promise.all([
    supabase.from('skills').select('*').order('name'),
    supabase
      .from('runs')
      .select('*, skills(name, slug)')
      .order('started_at', { ascending: false })
      .limit(10),
    supabase.from('status_counts').select('*').single(),
  ]);

  const skills: Skill[] = skillsRes.data ?? [];

  const runs: RunWithSkill[] = (runsRes.data ?? []).map((r: Record<string, unknown>) => {
    const skillRef = r.skills as { name: string; slug: string } | null;
    return {
      id: r.id as string,
      skill_id: r.skill_id as string,
      started_at: r.started_at as string,
      ended_at: r.ended_at as string | null,
      status: r.status as RunWithSkill['status'],
      output: r.output as string | null,
      triggered_by: r.triggered_by as RunWithSkill['triggered_by'],
      host: r.host as RunWithSkill['host'],
      skill_name: skillRef?.name ?? 'Unknown',
      skill_slug: skillRef?.slug ?? '',
    };
  });

  const counts: StatusCounts | null = countsRes.data ?? null;

  return { skills, runs, counts };
}

export default async function HomePage() {
  const { skills, runs, counts } = await fetchData();

  const byDomain = DOMAINS.reduce<Record<string, Skill[]>>((acc, domain) => {
    acc[domain] = skills.filter((s) => s.domain === domain);
    return acc;
  }, {} as Record<string, Skill[]>);

  return (
    <div className="min-h-screen bg-gray-50">
      <StatusHeader counts={counts} totalSkills={skills.length} />
      <main className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 gap-3">
          {DOMAINS.map((domain) => (
            <DomainColumn key={domain} domain={domain} skills={byDomain[domain]} />
          ))}
        </div>
        <RunHistory runs={runs} />
      </main>
    </div>
  );
}
