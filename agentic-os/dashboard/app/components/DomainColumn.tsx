import { Skill } from '@/lib/types';
import SkillCard from './SkillCard';

interface DomainColumnProps {
  domain: string;
  skills: Skill[];
}

export default function DomainColumn({ domain, skills }: DomainColumnProps) {
  return (
    <div className="flex flex-col gap-2 min-w-0">
      <div className="flex items-center justify-between">
        <h2 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 truncate">
          {domain}
        </h2>
        <span className="text-[10px] text-gray-400 shrink-0 ml-1">{skills.length}</span>
      </div>
      <div className="flex flex-col gap-2">
        {skills.length === 0 ? (
          <div className="border border-dashed border-gray-200 rounded p-2 text-[10px] text-gray-300 text-center">
            no skills
          </div>
        ) : (
          skills.map((skill) => <SkillCard key={skill.id} skill={skill} />)
        )}
      </div>
    </div>
  );
}
