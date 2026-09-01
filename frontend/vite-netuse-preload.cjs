// vite 8 在模块加载期无条件 exec("net use")（Windows 网络盘探测，见其 optimizeSafeRealPathSync）。
// 受限沙箱禁止子进程 spawn，导致该调用抛 EPERM、vite/vitest 完全不可用。
// 本 preload 把该探测替换为空操作：不 spawn，回调空输出（= 无网络盘映射）。
// 对本地普通路径无任何影响；仅在受限沙箱环境下需要。通过 NODE_OPTIONS="--require=..." 注入。
const cp = require("child_process");
const origExec = cp.exec;
cp.exec = function (cmd, opts, cb) {
  if (typeof cmd === "string" && cmd.trim() === "net use") {
    const fn = typeof cb === "function" ? cb : typeof opts === "function" ? opts : null;
    if (fn) process.nextTick(fn, null, "", "");
    return { on() {}, once() {}, emit() {} };
  }
  return origExec.apply(this, arguments);
};
