import { useState, type FormEvent } from "react";
import { useChat } from "../../store";
import { useChatStream } from "../../hooks/useChatStream";

export default function ChatInput() {
  const [text, setText] = useState("");
  const { appendMessage } = useChat();
  const { send, isGenerating } = useChatStream();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const msg = text.trim();
    if (!msg || isGenerating) return;
    setText("");
    appendMessage({ role: "user", content: msg });
    void send(msg);
  };

  return (
    <div className="absolute bottom-0 inset-x-0 p-6 bg-gradient-to-t from-[#050505] via-[#050505] to-transparent pointer-events-none">
      <div className="max-w-4xl mx-auto pointer-events-auto">
        <form id="chat-form" onSubmit={submit} className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-cyber-blue/20 to-cyber-purple/20 rounded-xl blur opacity-30 group-focus-within:opacity-100 transition duration-500" />
          <div className="relative flex items-center bg-zinc-900 border border-zinc-700 cyber-input rounded-xl overflow-hidden transition-all duration-300">
            <div className="pl-5 text-cyber-blue font-mono font-bold animate-pulse">&gt;</div>
            <input
              id="chat-input"
              type="text"
              name="message"
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={isGenerating}
              className="w-full bg-transparent text-zinc-100 px-4 py-4 focus:outline-none focus:ring-0 font-sans text-base placeholder-zinc-600 selection:bg-cyber-blue selection:text-black disabled:opacity-50"
              placeholder="Enter directive…"
              autoComplete="off"
              required
            />
            <button
              id="submit-btn"
              type="submit"
              disabled={isGenerating}
              className="pr-5 pl-2 py-4 text-zinc-400 hover:text-cyber-green disabled:opacity-30 disabled:hover:text-zinc-400 focus-visible:text-cyber-green focus:outline-none transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1.5"
                  d="M14 5l7 7m0 0l-7 7m7-7H3"
                />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
