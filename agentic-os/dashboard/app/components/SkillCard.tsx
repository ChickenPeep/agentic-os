'use client';

import { useState } from 'react';
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

// Poll /api/run/[run_id] every 2s until status is success or failure.
// Max wait: 5 minutes (150 polls).
async function pollRunStatus(
  run_id: string,
  onUpdate: (status: string, output: string | null) => void
): Promise<void> {
  const MAX_POLLS = 150;
  const POLL_INTERVAL_MS = 2000;

  for (let i = 0; i < MAX_POLLS; i++) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

    try {
      const res = await fetch(`/api/run/${encodeURIComponent(run_id)}`);
      if (!res.ok) continue;

      const data: { status: string; output: string | null } = await res.json();
      onUpdate(data.status, data.output ?? null);

      if (data.status === 'success' || data.status === 'failure') {
        return;
      }
    } catch {
      // Network hiccup — keep polling
    }
  }

  // Timed out
  onUpdate('failure', 'Timed out waiting for skill to complete (5 min limit).');
}

export default function SkillCard({ skill }: SkillCardProps) {
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<string | null>(null);

  async function handleRun() {
    if (running) return;
    setRunning(true);
    setRunStatus('queued');

    try {
      // 1. Fire the run — returns immediately with run_id
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_slug: skill.slug }),
      });

      const data: { run_id?: string; error?: string; status?: string } = await res.json();

      if (!res.ok || data.error) {
        alert(`Failed to start run: ${data.error ?? res.statusText}`);
        setRunning(false);
        setRunStatus(null);
        return;
      }

      const { run_id } = data;
      if (!run_id) {
        alert('No run_id returned from server');
        setRunning(false);
        setRunStatus(null);
        return;
      }

      setRunStatus('running');

      // 2. Poll until done
      await pollRunStatus(run_id, (status, output) => {
        setRunStatus(status);
        if (status === 'success' || status === 'failure') {
          const label = status === 'success' ? 'Done' : 'Failed';
          alert(
            `${label}: ${skill.slug}\n\nRun ID: ${run_id}\n\nOutput:\n${output ?? '(no output)'}`
          );
        }
      });
    } catch (err) {
      alert(`Error: ${String(err)}`);
    } finally {
      setRunning(false);
      setRunStatus(null);
      // Reload to update the Recent Runs table
      window.location.reload();
    }
  }

  const buttonLabel = (() => {
    if (!running) return 'Run';
    if (runStatus === 'queued') return 'Queuing...';
    if (runStatus === 'running') return 'Running...';
    return 'Finishing...';
  })();

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
        disabled={skill.status !== 'active' || running}
        className="mt-1 w-full rounded bg-gray-800 text-white py-1 text-[10px] font-medium hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {buttonLabel}
      </button>
      {running && (
        <div className="flex items-center gap-1 text-[10px] text-gray-400">
          <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          {runStatus === 'running' ? 'Waiting for completion...' : 'Starting skill...'}
        </div>
      )}
    </div>
  );
}
