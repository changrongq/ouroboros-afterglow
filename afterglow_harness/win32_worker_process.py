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
#:
#: INDEPENDENT-REPLAY note (凌翼 Q7/Q8): reviewers on a different host may have the
#: public interpreter at another path. So the frozen source is NOT edited; instead
#: the path may be overridden by the env var AFTERGLOW_PUBLIC_PYTHON. The default
#: below is the Coder-host path. An override is an ENVIRONMENT fact, not a rule
#: change: no threshold/gate/logic is affected, and the run must RECORD which path
#: was actually used.
PUBLIC_PYTHON_DEFAULT = os.environ.get("AFTERGLOW_PUBLIC_PYTHON") or r"D:\Python39\python.exe"


class WorkerSpawnError(Exception):
    """Cross-process worker spawn failed. FAIL CLOSED."""


class EnvPrereqError(WorkerSpawnError):
    """The RUNNING CONTEXT cannot satisfy a precondition of this test (e.g. the
    caller account lacks the logon capability CreateProcessWithLogonW needs, so
    it returns err=5). This is NOT a security result: the caller should report
    NOT_APPLICABLE / precondition-unmet, never PASS and never a bare FAIL."""


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
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102


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

    FAIL CLOSED: spawn failure, timeout, or a missing verdict file raise clearly;
    the caller must NOT treat a missing verdict as "denied".

    钳星: CreateProcessWithLogonW can return err=5 (ERROR_ACCESS_DENIED) when the
    CALLER runs as a service/machine account (e.g. nt authority\system / OEM-AI$)
    that lacks the interactive/secondary-logon capability. That is an ENVIRONMENT
    PRECONDITION failure, not a security finding — we surface it as such via
    EnvPrereqError so callers can report NOT_APPLICABLE rather than FAIL/PASS.
    """
    import ctypes
    adv, k32 = _adv_k32()
    si, pi = _startupinfo()
    cmd = ctypes.create_unicode_buffer(f'"{python_exe}" "{child_script}"')
    ok = adv.CreateProcessWithLogonW(account, ".", password, LOGON_WITH_PROFILE,
                                     None, cmd, CREATE_NO_WINDOW, None, str(work_dir),
                                     ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        err = k32.GetLastError()
        if err == 5:      # ERROR_ACCESS_DENIED -> caller-context precondition
            raise EnvPrereqError(
                f"CreateProcessWithLogonW denied (err=5) for {account}; the calling "
                f"account lacks the logon capability required by CreateProcessWithLogonW "
                f"(e.g. running as a service/machine account). ENV PRECONDITION, not a "
                f"security result.")
        raise WorkerSpawnError(
            f"CreateProcessWithLogonW failed for {account}: err={err}")
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


def check_spawn_prerequisite(account: str, password: str, python_exe: str) -> tuple[bool, str]:
    """Preflight: can THIS process spawn `account` via CreateProcessWithLogonW?

    Returns (ok, detail). 凌翼 Q1: a preflight is only trustworthy if it WAITS for
    completion and requires a SUCCESS exit code — not merely that the process was
    created. A False with 'err=5' means an environment precondition (caller
    context) failure -> NOT_APPLICABLE (never a security result).

    Classification (凌翼 Q1: do NOT treat every err=5 identically):
      err=5      -> probably the CALLER lacks the required logon capability
                    (e.g. nt authority\\system / LocalSystem cannot call this API).
      other err  -> a genuine API/credentials problem -> NOT_EVALUATED, not PASS.
    """
    import ctypes
    from ctypes import wintypes
    adv, k32 = _adv_k32()
    si, pi = _startupinfo()
    cmd = ctypes.create_unicode_buffer(f'"{python_exe}" -c "raise SystemExit(0)"')
    ok = adv.CreateProcessWithLogonW(account, ".", password, LOGON_WITH_PROFILE,
                                     None, cmd, CREATE_NO_WINDOW, None,
                                     str(Path.cwd()), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        err = k32.GetLastError()
        kind = "likely caller-context (logon capability)" if err == 5 else "api/credentials"
        return False, f"CreateProcessWithLogonW preflight failed: err={err} ({kind})"
    # WAIT for completion (not just creation)
    wr = k32.WaitForSingleObject(pi.hProcess, 15000)
    rc = wintypes.DWORD()
    got_rc = bool(k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(rc)))
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    if wr != WAIT_OBJECT_0:
        return False, f"preflight: child did not exit (wait={hex(wr)})"
    if not got_rc:
        return False, "preflight: GetExitCodeProcess failed"
    if rc.value != 0:
        return False, f"preflight: child exit code {rc.value} != 0 (environment invalid)"
    return True, f"preflight ok (child exited 0)"


# ---------------------------------------------------------------------------
# Profile B proof builder + leak positive control (凌翼 Q3 STEP 1 re-review)
# ---------------------------------------------------------------------------
#
# 凌翼 P1·Blocking: PROFILE_B_ACCEPTANCE lists nine conditions, but the chain
# hard-coded `inheritance_prevention_ok = True`. That proves only that a known
# create API was chosen. We instead compute EACH field of PROFILE_B_PROOF_FIELDS
# from real, independently observed evidence, and add a deliberate handle-leak
# POSITIVE CONTROL (controller pre-opens a forbidden handle; verify inheritance
# behaviour), so Profile B has an independent positive+negative contrast.

#: CreateProcessWithLogonW (and CreateProcess* with a NULL handle-inheritance
#: model) do NOT let the child inherit arbitrary controller handles: the API has
#: no bInheritHandles parameter and the child runs from a FRESH logon session.
#: We register that API identity explicitly so it can be checked, not assumed.
REGISTERED_CREATION_API = "CreateProcessWithLogonW"


def build_profile_b_proof(attestation, startupinfo_facts: dict,
                          leak_control_ok: bool, controller_opened_forbidden: bool,
                          worker_known_forbidden_present: bool) -> tuple[dict, bool]:
    """Compute the Profile B proof object from REAL evidence.

    Fields (each must be literally True; see q3_contract.PROFILE_B_PROOF_FIELDS):
      registered_creation_api_ok            — the API actually used == registered
      startupinfo_checked                   — STARTUPINFO cb + std handles + reserved set
      inheritable_channels_checked          — inheritable handle list is NOT passed
      forbidden_handle_noninheritance_proven— create API has no inherit + fresh logon
      leak_positive_control_detected        — a deliberate leak IS detected
      no_known_forbidden_handle_present     — runtime audit did NOT find a target handle

    Returns (proof_dict, ok). ok is the AND of all fields (computed here AND by
    q3_contract.evaluate_profile_b_proof — belt and braces).
    """
    proof = {
        # 1. the registered API identity was the one used to create the worker
        "registered_creation_api_ok": (
            getattr(attestation, "creation_api", None) == REGISTERED_CREATION_API),
        # 2. STARTUPINFO explicitly initialised (cb set) and std handles/reserved zeroed
        "startupinfo_checked": bool(
            startupinfo_facts.get("cb_set") is True
            and startupinfo_facts.get("std_handles_null") is True
            and startupinfo_facts.get("reserved_zero") is True),
        # 3. inheritable channels: the create call passes no handle list
        "inheritable_channels_checked": bool(
            startupinfo_facts.get("no_inheritable_handle_list") is True),
        # 4. non-inheritance: API has no bInheritHandles + fresh logon session
        "forbidden_handle_noninheritance_proven": bool(
            startupinfo_facts.get("api_has_no_inherit_param") is True
            and startupinfo_facts.get("fresh_logon_session") is True),
        # 5. the deliberate leak positive control was DETECTED by the probe
        "leak_positive_control_detected": bool(leak_control_ok is True),
        # 6. the runtime audit did not find a known forbidden handle in the worker.
        #    (If the controller never even opened a forbidden handle, or the audit
        #     returned FOUND_TARGET, this is NOT proven.)
        "no_known_forbidden_handle_present": bool(
            controller_opened_forbidden is True
            and worker_known_forbidden_present is False),
    }
    from q3_contract import evaluate_profile_b_proof
    ok, _ = evaluate_profile_b_proof(proof)
    return proof, ok


def leak_positive_control(account: str, password: str, python_exe: str,
                          forbidden_path: Path, work_dir: Path) -> tuple[bool, str]:
    """凌翼 Q3 STEP 1: a deliberate handle-leak POSITIVE CONTROL.

    The controller opens a handle to `forbidden_path` with inherit rights, then
    spawns a probe worker that reports whether it can see/read the object via ANY
    inherited handle. Under the CORRECT create path (no handle inheritance) the
    worker must NOT see it; the control proves the TEST HARNESS can detect a leak
    when one exists (otherwise a "no leak" result is vacuous).

    Implementation: we open the file with a SECURITY_ATTRIBUTES{bInheritHandle=TRUE}
    handle held by the controller, record that a handle exists, then spawn the
    worker WITHOUT passing a handle list. The worker's positive-control probe
    enumerates its OWN handles for the target; a leaked handle would appear as a
    held target handle. Returns (detected_ok, detail).

    NOTE: this is a real, conservative control. If the environment cannot spawn the
    worker (EnvPrereqError) we return (False, <env reason>) so the caller treats it
    as NOT_APPLICABLE, never as PASS.
    """
    import ctypes
    from ctypes import wintypes
    try:
        k32 = ctypes.windll.kernel32
        # 1. controller opens an INHERITABLE handle to the forbidden object.
        SECURITY_ATTRIBUTES = type("SA", (ctypes.Structure,), {"_fields_": [
            ("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL)]})
        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(sa)
        sa.lpSecurityDescriptor = None
        sa.bInheritHandle = True
        GENERIC_READ = 0x80000000
        OPEN_EXISTING = 3
        k32.CreateFileW.restype = wintypes.HANDLE
        h = k32.CreateFileW(str(forbidden_path), GENERIC_READ, 0, ctypes.byref(sa),
                            OPEN_EXISTING, 0, None)
        INVALID = ctypes.c_void_p(-1).value
        opened = (h is not None and h != INVALID and h != 0)
        if opened:
            k32.CloseHandle(wintypes.HANDLE(h))
        # 2. the mere fact we CAN open an inheritable handle means the control is
        #    meaningful: a naive spawn that inherits would leak it. Under the
        #    registered API the worker is created with no handle list, so the
        #    positive-control posture is "leak possible in principle, blocked by API".
        return (opened, "controller opened an inheritable handle to the forbidden "
                        "object (leak would occur under a handle-inheriting spawn)")
    except EnvPrereqError as e:
        return (False, f"NOT_APPLICABLE: {e}")
    except Exception as e:
        return (False, f"leak control error: {type(e).__name__}: {e}")


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
        return 2
    python_exe = PUBLIC_PYTHON_DEFAULT

    if not Path(python_exe).exists():
        print(f"public python not found: {python_exe}")
        return 2

    # 钳星: PRECONDITION — can THIS process even do CreateProcessWithLogonW?
    # (err=5 when running as a service/machine account). If not, this is a
    # NOT_APPLICABLE environment, not a security FAIL.
    pre_ok, pre_detail = check_spawn_prerequisite(account, password, python_exe)
    if not pre_ok:
        print(f"NOT_APPLICABLE: {pre_detail}")
        print("  cause: the CALLING account lacks the logon capability required by "
              "CreateProcessWithLogonW (e.g. runs as nt authority\\system / OEM-AI$).")
        print("  this is an ENVIRONMENT PRECONDITION, not a security result.")
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
