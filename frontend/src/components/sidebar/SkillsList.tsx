import { useStatus } from "../../hooks/useStatus";

export default function SkillsList() {
  const { skills } = useStatus();

  return (
    <div className="p-6 border-b border-cyber-border flex-1 overflow-y-auto min-h-[150px]">
      <h2 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-4 flex items-center">
        <svg
          className="w-3 h-3 mr-2 text-zinc-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
          />
        </svg>
        Active Skills
      </h2>
      <ul id="skills-list" className="space-y-4">
        {skills.length === 0 ? (
          <li className="text-xs text-zinc-600 font-mono italic">Initializing modules...</li>
        ) : (
          skills.map((skill) => (
            <li key={skill.name} className="hud-border bg-zinc-900/50 p-3 rounded-sm">
              <div className="flex items-center mb-1">
                <span
                  className={`flex-shrink-0 h-1.5 w-1.5 rounded-full ${
                    skill.active ? "bg-cyber-green shadow-[0_0_5px_#00ffa3]" : "bg-zinc-600"
                  } mr-2`}
                />
                <p className="text-xs font-mono font-medium text-zinc-300">{skill.name}</p>
              </div>
              <p
                className="text-[10px] text-zinc-500 mt-1 line-clamp-2 leading-relaxed"
                title={skill.description}
              >
                {skill.description}
              </p>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
