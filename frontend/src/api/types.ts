// 与 core/loop.py / core/session.py / core/memory.py / app.py 响应对应（字段名逐一核实，勿改）

// ---- SSE 事件（core/loop.py 逐一核实）----
export type ChatEvent =
  | { type: "text_delta"; content: string }
  | { type: "tool_call_start"; id: string; name: string; arguments: string }
  | {
      type: "tool_call_end";
      id: string;
      name: string;
      result_summary: string;
      approved?: boolean;
    }
  | {
      type: "token_usage";
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    }
  | {
      type: "approval_required";
      approval_id: string;
      id: string;
      name: string;
      arguments: string;
      risk_level: string;
      reason: string;
    }
  | {
      type: "approval_resolved";
      approval_id: string;
      id: string;
      name: string;
      approved: boolean;
    }
  | { type: "error"; content: string }
  | { type: "turn_end"; new_messages?: unknown[] };

// ---- /api/status ----
export interface StatusResponse {
  skills: { name: string; description: string; active: boolean }[];
  tools: { name: string; description: string }[];
}

// ---- /api/sessions ----
export interface SessionItem {
  session_id: string;
  message_count: number;
  last_active: string | null;
}

// ---- /api/stats ----
export interface StatsResponse {
  totals: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    rounds: number;
    tool_calls: number;
    estimated_cost: number | null;
  };
  tool_call_stats: { tool: string; count: number; last_used: string }[];
  recent_tool_calls: {
    tool: string;
    arguments: string;
    result_summary: string;
    created_at: string;
  }[];
  recent_rounds: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    created_at: string;
  }[];
}

// ---- /api/outputs ----
export interface OutputFile {
  name: string;
  size: number;
  mtime: number;
}

// ---- /api/memory ----
export interface MemoryResponse {
  stats: { total_messages_in_window: number; has_long_term_memory: boolean };
  long_term_memory: string;
}

// ---- /api/history（OpenAI 消息格式，与 core/loop.py 内部 messages 一致）----
export interface HistoryMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: {
    id: string;
    type: string;
    function: { name: string; arguments: string };
  }[];
  tool_call_id?: string;
  name?: string;
}
export interface HistoryResponse {
  messages: HistoryMessage[];
  tokens: { prompt: number; completion: number };
}

// ---- /api/approve ----
export interface ApproveResponse {
  status: "ok" | "error";
  approved?: boolean;
  message?: string;
}
