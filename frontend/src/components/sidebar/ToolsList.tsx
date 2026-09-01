import { useStatus } from "../../hooks/useStatus";

export default function ToolsList() {
  const { tools } = useStatus();

  return (
    <div className="p-6 bg-zinc-900/30">
      <h2 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-4 flex items-center">
        <svg className="w-3 h-3 mr-2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        Core Tools
      </h2>
      <ul id="tools-list" className="space-y-3">
        {tools.length === 0 ? (
          <li className="text-xs text-zinc-600 font-mono italic">Scanning registry...</li>
        ) : (
          tools.map((tool) => (
            <li
              key={tool.name}
              className="flex items-baseline space-x-2 border-l-2 border-zinc-800 pl-2 opacity-80 hover:opacity-100 transition-opacity"
            >
              <span className="text-[11px] font-mono text-cyber-blue">{tool.name}()</span>
              <span className="text-[10px] text-zinc-500 line-clamp-2 leading-relaxed">{tool.description}</span>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
