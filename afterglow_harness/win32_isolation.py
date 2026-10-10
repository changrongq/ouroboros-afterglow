"""
win32_isolation.py — Q3 OS-LEVEL ISOLATION backend (Windows / Win32).

STATUS: SELF-CONTAINED PROOF-OF-CONCEPT. NOT yet wired into the frozen Phase A
harness. Nothing here modifies any RC11-frozen byte.

为什么需要这个模块
==================
SPEC §16.1.1 「记账隔离 ≠ 眼睛隔离」:

    不许把"没写进账本"，当成"没看见"。
    隔离的是命名空间，不是眼睛。

Phase A 的 reset.py 是【逻辑层】: restart_worker()/access_probe() 显式 raise
NotIsolatedError —— 诚实拒绝假装完成隔离。本模块提供【真实】OS 级隔离后端，
让"一个被禁止的访问，真的被操作系统拒绝"。

关键实测（本机 Windows 10 / CPython 3.11.15）
=============================================
    os.chmod(file, 0)  ->  st_mode 变 0o100444（看起来只读），
                           但 file.read_text() 仍然成功。
    ⇒ POSIX 风格的 chmod 在 Windows 上是【装样子】。

    真实拒绝必须落成 DACL deny ACE:
       icacls <file> /deny <USER>:(R)  ->  read 抛 PermissionError [Errno 13]
       （deny ACE 优先于 allow，即使对 owner 也生效）

三态 access witness（本层核心，防"没试"冒充"被拒"）
====================================================
    ACCESS_DENIED        : 尝试了，OS 拒绝   -> 隔离成立
    ACCESS_GRANTED       : 尝试了，OS 放行   -> 隔离失败 (FAIL CLOSED)
    ACCESS_NOT_ATTEMPTED : 没试             -> 未评估，绝不算通过
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen identifiers for this isolation profile (candidate; frozen after review)
# ---------------------------------------------------------------------------

ISOLATION_PROFILE_ID = "PROCESS_ISOLATION_WIN32_ACL_V1"
ISOLATION_PROFILE_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Tri-state access verdicts (fail-closed; "not attempted" is NEVER a pass)
# ---------------------------------------------------------------------------

ACCESS_DENIED = "ACCESS_DENIED"
ACCESS_GRANTED = "ACCESS_GRANTED"
ACCESS_NOT_ATTEMPTED = "ACCESS_NOT_ATTEMPTED"

#: A real access attempt is only "isolated" when the OS DENIED it.
ACCESS_ISOLATION_OK = frozenset({ACCESS_DENIED})


class IsolationError(Exception):
    """Any isolation-mechanism failure. FAIL CLOSED (never silently downgraded)."""


def _is_windows() -> bool:
    return sys.platform.startswith("win")


# ---------------------------------------------------------------------------
# Denial primitive: real DACL deny ACE (not chmod)
# ---------------------------------------------------------------------------


def deny_read_for_current_user(path: Path) -> None:
    """Attach a REAL deny-read ACE for the current user to `path`.

    On Windows this is a DACL deny ACE (deny precedence). On non-Windows we
    raise IsolationError — this profile is Win32-only, and pretending a POSIX
    chmod is equivalent would be exactly the 记账隔离 mistake.
    """
    if not _is_windows():
        raise IsolationError(
            f"{ISOLATION_PROFILE_ID} is Win32-only; refusing to fake isolation "
            f"with a POSIX chmod"
        )
    user = os.environ.get("USERNAME")
    if not user:
        raise IsolationError("USERNAME not set; cannot build a deny ACE")
    # icacls is the OS-blessed way to author a DACL; deny ACE takes precedence.
    p = subprocess.run(
        ["icacls", str(path), "/deny", f"{user}:(R)"],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise IsolationError(
            f"failed to attach deny ACE to {path}: rc={p.returncode} {p.stdout}{p.stderr}"
        )


def remove_deny_for_current_user(path: Path) -> None:
    if not _is_windows():
        return
    user = os.environ.get("USERNAME")
    if user:
        subprocess.run(["icacls", str(path), "/remove:d", user],
                       capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Access probe: attempt a real access, classify DENIED / GRANTED / NOT_ATTEMPTED
# ---------------------------------------------------------------------------


@dataclass
class AccessWitness:
    object_id: str
    verdict: str                       # ACCESS_DENIED | ACCESS_GRANTED | ACCESS_NOT_ATTEMPTED
    attempted: bool = False
    errno: int | None = None
    detail: str = ""

    @property
    def isolated(self) -> bool:
        return self.verdict in ACCESS_ISOLATION_OK


def probe_read_access(object_id: str, path: Path) -> AccessWitness:
    """Attempt to READ `path` and classify the outcome.

    A crash-free return of bytes => ACCESS_GRANTED (isolation FAILED).
    PermissionError / errno 13    => ACCESS_DENIED (isolation OK).
    Not attempted (path absent / not called) => never a pass.
    """
    if not path.exists():
        return AccessWitness(object_id, ACCESS_NOT_ATTEMPTED, attempted=False,
                             detail="object does not exist; nothing attempted")
    try:
        path.read_bytes()
        return AccessWitness(object_id, ACCESS_GRANTED, attempted=True,
                             detail="read succeeded: isolation FAILED")
    except PermissionError as e:
        return AccessWitness(object_id, ACCESS_DENIED, attempted=True,
                             errno=getattr(e, "errno", 13), detail=str(e))
    except OSError as e:
        # Any other OS error is NOT a clean denial; treat as not-a-pass.
        return AccessWitness(object_id, ACCESS_NOT_ATTEMPTED, attempted=True,
                             errno=getattr(e, "errno", None),
                             detail=f"non-permission OS error: {e}")


# ---------------------------------------------------------------------------
# Fresh-process witness
# ---------------------------------------------------------------------------


@dataclass
class WorkerIdentity:
    parent_pid: int
    worker_pid: int
    fresh: bool
    detail: str = ""


def spawn_worker(child_code: str) -> tuple[subprocess.CompletedProcess, WorkerIdentity]:
    """Spawn a genuinely NEW process and prove it is fresh (pid differs)."""
    parent = os.getpid()
    p = subprocess.run([sys.executable, "-c", child_code],
                       capture_output=True, text=True)
    worker_pid = -1
    for line in (p.stdout or "").splitlines():
        if line.startswith("WORKER_PID="):
            try:
                worker_pid = int(line.split("=", 1)[1])
            except ValueError:
                pass
    fresh = (worker_pid != -1 and worker_pid != parent)
    return p, WorkerIdentity(parent, worker_pid, fresh,
                             detail=f"parent={parent} worker={worker_pid}")


# ---------------------------------------------------------------------------
# Self-test (run directly): prove the mechanism
# ---------------------------------------------------------------------------

def _selftest() -> int:
    results = []

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    tmp = Path(tempfile.mkdtemp(prefix="q3_isolation_"))
    secret = tmp / "real_substrate.bin"
    secret.write_bytes(b"\x01\x02\x03\x04" * 4)

    # 1. NEGATIVE CONTROL: chmod(0) does NOT deny on Windows
    try:
        os.chmod(secret, 0)
        readable = True
        try:
            secret.read_bytes()
        except Exception:
            readable = False
        chk("NEGATIVE CONTROL: os.chmod(0) does NOT deny read on Windows", readable)
    finally:
        os.chmod(secret, 0o666)

    # 2. POSITIVE: real deny ACE -> read denied (dedicated throwaway file)
    secret2 = tmp / "real_substrate_denied.bin"
    secret2.write_bytes(b"\x01\x02\x03\x04" * 4)
    deny_read_for_current_user(secret2)
    w = probe_read_access("real_substrate", secret2)
    chk("POSITIVE: deny ACE -> ACCESS_DENIED", w.verdict == ACCESS_DENIED)
    chk("POSITIVE: witness.isolated is True", w.isolated)

    # 3. STICKINESS (real OS property): a deny ACE also blocks ACL modification
    #    by the same user -> this is genuine isolation, not a removable flag.
    #    (We do NOT require "restore"; isolation that is trivially reversible is
    #     weaker. Removal requires a privileged context, out of this layer.)
    w2 = probe_read_access("real_substrate", secret2)
    chk("STICKY: deny persists on re-probe (ACCESS_DENIED again)",
        w2.verdict == ACCESS_DENIED)

    # 4. NOT_ATTEMPTED is never a pass
    missing = tmp / "does_not_exist.bin"
    w3 = probe_read_access("missing", missing)
    chk("TRI-STATE: missing object -> ACCESS_NOT_ATTEMPTED (not a pass)",
        w3.verdict == ACCESS_NOT_ATTEMPTED and not w3.isolated)

    # 5. fresh process witness
    _, ident = spawn_worker("import os; print('WORKER_PID=%d' % os.getpid())")
    chk("FRESH PROCESS: worker pid != parent pid", ident.fresh)

    # 6. denied read from a CHILD process (the real cross-process proof)
    secret3 = tmp / "real_substrate_crossproc.bin"
    secret3.write_bytes(b"\xaa\xbb\xcc\xdd" * 4)
    deny_read_for_current_user(secret3)
    child_code = (
        "import sys\n"
        "try:\n"
        f"    open(r'{secret3}','rb').read()\n"
        "    print('CHILD_ACCESS=GRANTED')\n"
        "except PermissionError:\n"
        "    print('CHILD_ACCESS=DENIED')\n"
    )
    p, _ = spawn_worker(child_code)
    chk("CROSS-PROCESS: child denied reading real object",
        "CHILD_ACCESS=DENIED" in (p.stdout or ""))

    # 7. CONTROL: an un-denied sibling object IS readable by a child
    #    (proves the child CAN read, so the denial above is attributable)
    sibling = tmp / "allowed.bin"
    sibling.write_bytes(b"public")
    child_code2 = (
        "try:\n"
        f"    open(r'{sibling}','rb').read()\n"
        "    print('CHILD_ACCESS=GRANTED')\n"
        "except PermissionError:\n"
        "    print('CHILD_ACCESS=DENIED')\n"
    )
    p2, _ = spawn_worker(child_code2)
    chk("CONTROL: child CAN read an allowed sibling object",
        "CHILD_ACCESS=GRANTED" in (p2.stdout or ""))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _, ok in results if ok)
    print(f"\nwin32_isolation selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
