import { RunWithSkill } from '@/lib/types';

interface RunHistoryProps {
  runs: RunWithSkill[];
}

const RUN_STATUS_COLORS: Record<string, string> = {
  success: 'text-green-600',
  failure: 'text-red-600',
  running: 'text-blue-600',
};

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

export default function RunHistory({ runs }: RunHistoryProps) {
  return (
    <div className="mt-4 border border-gray-200 rounded">
      <div className="px-3 py-2 border-b border-gray-200 bg-gray-50">
        <h2 className="text-xs font-semibold text-gray-700">Recent Runs</h2>
      </div>
      {runs.length === 0 ? (
        <div className="px-3 py-4 text-xs text-gray-400 text-center">No runs yet.</div>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 text-gray-500">
              <th className="text-left px-3 py-1.5 font-medium">Time</th>
              <th className="text-left px-3 py-1.5 font-medium">Skill</th>
              <th className="text-left px-3 py-1.5 font-medium">Status</th>
              <th className="text-left px-3 py-1.5 font-medium">Triggered by</th>
              <th className="text-left px-3 py-1.5 font-medium">Output</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-1.5 text-gray-500 whitespace-nowrap">
                  {formatTime(run.started_at)}
                </td>
                <td className="px-3 py-1.5 font-mono text-gray-700">{run.skill_name}</td>
                <td className={`px-3 py-1.5 font-medium ${RUN_STATUS_COLORS[run.status] ?? 'text-gray-600'}`}>
                  {run.status}
                </td>
                <td className="px-3 py-1.5 text-gray-500">{run.triggered_by ?? '-'}</td>
                <td className="px-3 py-1.5 text-gray-500 truncate max-w-[200px]">
                  {run.output ? run.output.slice(0, 60) + (run.output.length > 60 ? '...' : '') : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
