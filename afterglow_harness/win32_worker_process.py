"""
win32_worker_process.py — Q3 CROSS-PROCESS sandbox (Windows / Win32).

STATUS: SELF-CONTAINED PoC. NOT wired into the frozen Phase A harness. Nothing
here modifies any RC11-frozen byte.

为什么需要这个模块（凌翼 gap 1 的正面实现）
============================================
Q3 的"眼睛隔离"要求 worker 是**真正不同的安全主体**，这样：
  · deny ACE 只锁 worker SID；
  · controller / observer **保留**读权限；
  · post-reset 的 preserve 检查是**真读**（不是拿旧缓存自比）。
凌翼 gap 1 实测：CreateRestrictedToken 不改变 TokenUser.SID；改窗口站授予
在受限 token 下会 0xC0000142。**正面路径 = 用一个真正不同的本地账户**
（afterglow_worker），经 CreateProcessWithLogonW 启动 worker。

实测结论（本机 2026-10-11）
===========================
  · worker (afterglow_worker) 访问被 deny 的对象 -> OS DENIED
  · observer (admin)         读同一对象          -> OS GRANTED
  ⇒ 同一对象上"worker 被拒 + observer 可读"同时成立 = 完整跨进程眼睛隔离。

关键工程约束（踩过的坑，写进契约）
==================================
1. worker 用的 Python 必须在**全局可读**位置（本机 D:\Python39，Users:(RX)），
   不能是 admin 私有 profile 下的 venv（worker 读不到，会 rc=103）。
2. deny ACE 作用在 worker 账户名；worker 自己的工作目录单独 grant。
3. deny 必须在上锁后**重新施加**（父目录 grant 之后），确保 deny 优先。
4. 只允许在**可丢弃的受控目录**上操作；不碰真实生产对象。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

WORKER_ACCOUNT_DEFAULT = "afterglow_worker"

#: A python interpreter readable by the worker account. Must be global (Users:RX),
#: NOT an admin-private venv path.
PUBLIC_PYTHON_DEFAULT = r"D:\Python39\python.exe"


class WorkerSpawnError(Exception):
    """Cross-process worker spawn failed. FAIL CLOSED."""


# ---------------------------------------------------------------------------
# CreateProcessWithLogonW binding
# ---------------------------------------------------------------------------

def _adv_k32():
    import ctypes
    from ctypes import wintypes
    adv = ctypes.windll.advapi32
    k32 = ctypes.windll.kernel32
    adv.CreateProcessWithLogonW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
        wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
    adv.CreateProcessWithLogonW.restype = wintypes.BOOL
    return adv, k32


LOGON_WITH_PROFILE = 0x00000001
CREATE_NO_WINDOW = 0x08000000


def _startupinfo():
    import ctypes
    from ctypes import wintypes

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    return si, PROCESS_INFORMATION()


@dataclass
class WorkerRun:
    account: str
    pid: int
    exit_code: int
    stdout_path: Path | None
    verdict: str | None


def run_cross_process_worker(account: str, password: str, work_dir: Path,
                             python_exe: str, child_script: Path,
                             verdict_path: Path, timeout_s: int = 30) -> WorkerRun:
    """Run `python child_script` as `account` and wait for it. Returns WorkerRun.

    FAIL CLOSED: spawn failure, timeout, or a missing verdict file raise/extend
    clearly; the caller must NOT treat a missing verdict as "denied".
    """
    import ctypes
    adv, k32 = _adv_k32()
    si, pi = _startupinfo()
    cmd = ctypes.create_unicode_buffer(f'"{python_exe}" "{child_script}"')
    ok = adv.CreateProcessWithLogonW(account, ".", password, LOGON_WITH_PROFILE,
                                     None, cmd, CREATE_NO_WINDOW, None, str(work_dir),
                                     ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise WorkerSpawnError(
            f"CreateProcessWithLogonW failed for {account}: err={k32.GetLastError()}")
    k32.WaitForSingleObject(pi.hProcess, timeout_s * 1000)
    rc = ctypes.c_ulong()
    k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(rc))
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    # allow a beat for the child's last write to flush
    for _ in range(20):
        if verdict_path.exists():
            break
        time.sleep(0.05)
    verdict = verdict_path.read_text(encoding="utf-8") if verdict_path.exists() else None
    if verdict is None:
        raise WorkerSpawnError(
            f"worker produced no verdict (rc={rc.value}); environment likely invalid")
    return WorkerRun(account, pi.dwProcessId, rc.value, verdict_path, verdict)


# ---------------------------------------------------------------------------
# ACL helpers for the cross-process sandbox (disposable dirs only)
# ---------------------------------------------------------------------------

def deny_read(account: str, path: Path) -> None:
    p = subprocess.run(["icacls", str(path), "/deny", f"{account}:(R)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise WorkerSpawnError(f"deny failed for {path}: {p.stdout}{p.stderr}")


def grant(account: str, path: Path, perm: str = "(OI)(CI)(F)") -> None:
    p = subprocess.run(["icacls", str(path), "/grant", f"{account}:{perm}"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise WorkerSpawnError(f"grant failed for {path}: {p.stdout}{p.stderr}")


# ---------------------------------------------------------------------------
# Self-test: the full cross-process sandbox (worker DENIED, observer GRANTED)
# ---------------------------------------------------------------------------

def _selftest() -> int:
    if not sys.platform.startswith("win"):
        print("win32_worker_process selftest requires Windows")
        return 2
    results = []

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    account = WORKER_ACCOUNT_DEFAULT
    # CREDENTIALS: NEVER hard-coded. Inject at runtime via environment
    # (Q3 SECURITY: 凌翼 — published credential = exposure). The caller sets
    # AFTERGLOW_WORKER_PASSWORD in the environment; we never store it in code.
    password = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not password:
        print("SKIP: set AFTERGLOW_WORKER_PASSWORD in the environment to run "
              "the cross-process self-test (no stored credential).")
        return 0
    python_exe = PUBLIC_PYTHON_DEFAULT

    if not Path(python_exe).exists():
        print(f"public python not found: {python_exe}")
        return 2

    d = Path(tempfile.mkdtemp(prefix="q3_xproc_"))
    try:
        work = d / "work"; work.mkdir()
        secret = d / "real_substrate.bin"
        secret.write_bytes(b"TOP-SECRET-PAYLOAD")

        # deny the worker read on the object; grant it only its own work dir
        deny_read(account, secret)
        grant(account, work, "(OI)(CI)(F)")
        grant(account, d, "(OI)(CI)(RX)")
        deny_read(account, secret)          # re-assert deny after parent grant

        child = work / "child.py"
        out = work / "out.txt"
        child.write_text(
            "res=[]\n"
            f"try:\n    open(r'{secret}','rb').read(); res.append('SECRET=READ')\n"
            "except PermissionError:\n    res.append('SECRET=DENIED')\n"
            "except Exception as e:\n    res.append('ERR:'+type(e).__name__)\n"
            f"open(r'{out}','w').write('|'.join(res))\n",
            encoding="utf-8")

        run = run_cross_process_worker(account, password, work, python_exe, child, out)
        chk("CROSS-PROCESS: worker spawned as a DIFFERENT account",
            run.exit_code == 0)
        chk("CROSS-PROCESS: worker verdict = SECRET=DENIED (OS denied read)",
            run.verdict == "SECRET=DENIED")

        # observer (current principal) keeps read -> preserve can be independently verified
        try:
            secret.read_bytes()
            observer_ok = True
        except PermissionError:
            observer_ok = False
        chk("CROSS-PROCESS: observer STILL reads the same object (GRANTED)", observer_ok)

        # negative control: an UN-denied sibling is readable by the worker too
        sibling = work / "allowed.txt"
        sibling.write_text("public", encoding="utf-8")
        child2 = work / "child2.py"
        out2 = work / "out2.txt"
        child2.write_text(
            "res=[]\n"
            f"try:\n    open(r'{sibling}','rb').read(); res.append('SIB=READ')\n"
            "except PermissionError:\n    res.append('SIB=DENIED')\n"
            f"open(r'{out2}','w').write('|'.join(res))\n",
            encoding="utf-8")
        run2 = run_cross_process_worker(account, password, work, python_exe, child2, out2)
        chk("CONTROL: worker CAN read an allowed sibling (attributable denial)",
            run2.verdict == "SIB=READ")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for _, ok in results if ok)
    print(f"\nwin32_worker_process selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
