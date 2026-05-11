import { StatusCounts } from '@/lib/types';

interface StatusHeaderProps {
  counts: StatusCounts | null;
  totalSkills: number;
}

export default function StatusHeader({ counts, totalSkills }: StatusHeaderProps) {
  return (
    <header className="border-b border-gray-200 bg-gray-900 text-white px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold tracking-tight">Agentic OS</h1>
        <span className="text-xs text-gray-400">Dashboard</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-300">
        <span>
          <span className="text-green-400 font-semibold">{counts?.active_skills ?? totalSkills}</span> active
        </span>
        <span>
          <span className="text-yellow-400 font-semibold">{counts?.paused_skills ?? 0}</span> paused
        </span>
        <span>
          <span className="text-blue-400 font-semibold">{counts?.routines ?? 0}</span> routines
        </span>
        <span>
          <span className="text-purple-400 font-semibold">{counts?.agents ?? 0}</span> agents
        </span>
      </div>
    </header>
  );
}
