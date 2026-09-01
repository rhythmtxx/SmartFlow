import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { usePolling } from "../../hooks/usePolling";
import { apiFetch } from "../../api/client";
import type { OutputFile } from "../../api/types";

/** 旧 JS formatBytes（static/index.html 677-684 行）逐字照抄 */
function formatBytes(bytes: number, decimals = 1): string {
  if (!+bytes) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

/** 新旧列表是否一致（按 name|size|mtime 签名比较，不一致时触发 ping） */
function fileSignature(files: OutputFile[]): string {
  return files.map((f) => `${f.name}|${f.size}|${f.mtime}`).join("\n");
}

/** Workspace Outputs 面板：列表轮询 + 上传/打开/删除（旧 static/index.html 407-433 / 686-810 行的 React 版） */
export default function OutputsPanel() {
  const [files, setFiles] = useState<OutputFile[]>([]);
  const [ping, setPing] = useState(false);
  const prevRef = useRef<OutputFile[] | null>(null);
  const pingTimer = useRef<number | null>(null);

  /** outputs-ping 圆点短暂闪烁（旧 JS 的 ping 动画：opacity-100，300ms 后恢复） */
  const flashPing = useCallback(() => {
    setPing(true);
    if (pingTimer.current !== null) window.clearTimeout(pingTimer.current);
    pingTimer.current = window.setTimeout(() => setPing(false), 300);
  }, []);

  // 卸载时清理 ping 定时器，避免卸载后 setState
  useEffect(() => {
    return () => {
      if (pingTimer.current !== null) window.clearTimeout(pingTimer.current);
    };
  }, []);

  /** 拉取 /api/outputs 并渲染列表（旧 fetchOutputs，686-728 行） */
  const fetchOutputs = useCallback(async () => {
    try {
      const res = await apiFetch("/api/outputs");
      if (!res.ok) return;
      const data = (await res.json()) as { files?: OutputFile[] };
      const next = data.files ?? [];
      const prev = prevRef.current;
      prevRef.current = next;
      // 文件更新（新旧列表不一致）→ ping 短暂闪烁
      if (!prev || fileSignature(prev) !== fileSignature(next)) flashPing();
      setFiles(next);
    } catch (error) {
      console.error("Failed to fetch outputs:", error);
    }
  }, [flashPing]);

  usePolling(fetchOutputs, 5000, [fetchOutputs]);

  /** 上传文件（旧 handleFileUpload，730-760 行；FormData 由 fetch 自动带 boundary，勿手动设 Content-Type） */
  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Show uploading state cursor
      document.body.style.cursor = "wait";
      const res = await apiFetch("/api/upload", { method: "POST", body: formData });
      const data = (await res.json()) as { status?: string; message?: string };
      if (data.status === "success") {
        // 刷新列表 + ping
        flashPing();
        void fetchOutputs();
      } else {
        console.error("Upload failed:", data.message);
        alert("Upload failed: " + data.message);
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload error.");
    } finally {
      document.body.style.cursor = "default";
      event.target.value = ""; // Reset input（允许重复上传同名文件）
    }
  };

  /** 带鉴权打开/下载输出文件（旧 openOutput，764-789 行）——禁止直接 <a href="/outputs/...">（鉴权失效） */
  const openOutput = async (filename: string) => {
    try {
      const res = await apiFetch(`/api/outputs/download/${encodeURIComponent(filename)}`);
      if (!res.ok) {
        alert("Failed to open file: " + res.status);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const isPptx = filename.toLowerCase().endsWith(".pptx");
      if (isPptx) {
        // PPTX 只能下载，无法在浏览器预览
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        window.open(url, "_blank");
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      console.error("Failed to open output:", error);
      alert("Failed to open file.");
    }
  };

  /** 删除输出文件（旧 deleteOutput，791-810 行） */
  const deleteOutput = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
      return;
    }
    try {
      const res = await apiFetch(`/api/outputs/${encodeURIComponent(filename)}`, { method: "DELETE" });
      const data = (await res.json()) as { status?: string; message?: string };
      if (data.status === "success") {
        void fetchOutputs();
      } else {
        alert("Error deleting file: " + data.message);
      }
    } catch (error) {
      console.error("Delete failed:", error);
      alert("Failed to delete the file.");
    }
  };

  const isPptx = (name: string) => name.toLowerCase().endsWith(".pptx");

  return (
    <div className="p-6 border-cyber-border flex-1 overflow-y-auto min-h-[50%] bg-zinc-900/30">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 flex items-center relative">
          <svg className="w-3 h-3 mr-2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"
            />
          </svg>
          Workspace Outputs
          <span
            id="outputs-ping"
            className={`absolute -right-4 top-1 w-1.5 h-1.5 rounded-full bg-cyber-blue transition-opacity duration-300 shadow-[0_0_4px_#00f0ff] ${
              ping ? "opacity-100" : "opacity-0"
            }`}
          />
        </h2>
        {/* Add File Upload Button */}
        <label
          htmlFor="file-upload"
          className="cursor-pointer text-zinc-400 hover:text-cyber-green transition-colors"
          title="Upload File to Workspace"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
            />
          </svg>
          <input id="file-upload" type="file" className="hidden" onChange={handleUpload} />
        </label>
      </div>
      <ul id="outputs-list" className="space-y-3">
        {files.length === 0 ? (
          <li className="text-xs text-zinc-600 font-mono italic">No artifacts detected...</li>
        ) : (
          files.map((f) => (
            <li
              key={f.name}
              className="flex items-center justify-between group py-1.5 border-b border-zinc-900/50 last:border-0 hover:bg-zinc-900/30 -mx-2 px-2 rounded transition-colors"
            >
              <div className="flex flex-col flex-1 min-w-0 pr-3">
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    void openOutput(f.name);
                  }}
                  className="text-xs font-mono text-zinc-300 hover:text-cyber-green truncate block font-medium transition-colors"
                >
                  {f.name}
                </a>
                <span className="text-[10px] text-zinc-600 font-mono tracking-wider mt-0.5">{formatBytes(f.size)}</span>
              </div>
              <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    void openOutput(f.name);
                  }}
                  className="text-zinc-500 hover:text-cyber-blue transition-colors flex-shrink-0"
                  title={isPptx(f.name) ? "Download" : "Open"}
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d={
                        isPptx(f.name)
                          ? "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                          : "M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      }
                    />
                  </svg>
                </a>
                <button
                  type="button"
                  onClick={() => void deleteOutput(f.name)}
                  className="text-zinc-500 hover:text-red-500 transition-colors flex-shrink-0 focus:outline-none cursor-pointer"
                  title="Delete"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
