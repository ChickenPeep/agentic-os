export interface Skill {
  id: string;
  domain: string;
  name: string;
  slug: string;
  description: string | null;
  type: 'skill' | 'routine' | 'agent';
  webhook_url: string | null;
  status: 'active' | 'paused' | 'retired';
  host: 'mac' | 'cloud';
  created_at: string;
  last_run_at: string | null;
  run_count: number;
}

export interface Run {
  id: string;
  skill_id: string;
  started_at: string;
  ended_at: string | null;
  status: 'running' | 'success' | 'failure';
  output: string | null;
  triggered_by: 'dashboard' | 'telegram' | 'cron' | 'plan_triage' | 'manual' | null;
  host: 'mac' | 'cloud' | null;
}

export interface RunWithSkill extends Run {
  skill_name: string;
  skill_slug: string;
}

export interface Plan {
  id: string;
  raw_text: string;
  triaged_at: string | null;
  action_taken: string | null;
  target_skill_id: string | null;
  status: 'pending' | 'triaged' | 'done';
  wiki_article_path: string | null;
}

export interface WikiArticle {
  id: string;
  domain: string;
  path: string;
  title: string;
  summary: string | null;
  source_raw_files: string[] | null;
  updated_at: string;
}

export interface StatusCounts {
  active_skills: number;
  paused_skills: number;
  retired_skills: number;
  routines: number;
  agents: number;
}

export const DOMAINS = [
  'MEMORY',
  'PRODUCTIVITY',
  'NEXUM',
  'CONSULTING',
  'SCHOOL',
  'FOOTBALL',
  'BIBLE STUDY',
  'SIDE PROJECTS',
  'PERSONAL OPS',
] as const;

export type Domain = (typeof DOMAINS)[number];
