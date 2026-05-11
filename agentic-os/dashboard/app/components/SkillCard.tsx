'use client';

import { Skill } from '@/lib/types';

interface SkillCardProps {
  skill: Skill;
}

const STATUS_COLORS: Record<Skill['status'], string> = {
  active: 'bg-green-100 text-green-800',
  paused: 'bg-yellow-100 text-yellow-800',
  retired: 'bg-gray-100 text-gray-600',
};

const TYPE_COLORS: Record<Skill['type'], string> = {
  skill: 'bg-blue-100 text-blue-700',
  routine: 'bg-orange-100 text-orange-700',
  agent: 'bg-purple-100 text-purple-700',
};

export default function SkillCard({ skill }: SkillCardProps) {
  async function handleRun() {
    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_slug: skill.slug }),
      });
      const data = await res.json();
      alert(
        `Run dispatched: ${skill.slug}\n\n` +
        JSON.stringify(data, null, 2)
      );
    } catch (err) {
      alert(`Error: ${String(err)}`);
    }
  }

  return (
    <div className="border border-gray-200 rounded p-2 bg-white text-xs flex flex-col gap-1">
      <div className="flex items-start justify-between gap-1">
        <span className="font-semibold text-gray-900 leading-tight">{skill.name}</span>
        <span className={`shrink-0 rounded px-1 py-0.5 text-[10px] font-medium ${STATUS_COLORS[skill.status]}`}>
          {skill.status}
        </span>
      </div>
      <div className="flex items-center gap-1">
        <span className={`rounded px-1 py-0.5 text-[10px] font-medium ${TYPE_COLORS[skill.type]}`}>
          {skill.type}
        </span>
        <span className="text-gray-400 text-[10px]">{skill.host}</span>
      </div>
      {skill.description && (
        <p className="text-gray-500 leading-tight line-clamp-2">{skill.description}</p>
      )}
      <button
        onClick={handleRun}
        disabled={skill.status !== 'active'}
        className="mt-1 w-full rounded bg-gray-800 text-white py-1 text-[10px] font-medium hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Run
      </button>
    </div>
  );
}
