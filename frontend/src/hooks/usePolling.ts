import { useEffect } from "react";

/**
 * 通用轮询：挂载立即执行一次，按 intervalMs 定时执行，卸载自动清理。deps 变化时重启。
 */
export function usePolling(
  fn: () => void | Promise<void>,
  intervalMs: number,
  deps: unknown[] = []
) {
  useEffect(() => {
    void fn();
    const t = setInterval(() => void fn(), intervalMs);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
