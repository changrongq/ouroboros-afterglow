"""Business worker ENTRY (PERSISTENT) — the real business process under the adapter.

This is NOT the Q3 short-lived probe. It is a long-running worker that:

  · starts and immediately signals "ready but HOLDING" (task NOT begun);
  · waits for an explicit RELEASE token before processing any real input;
  · while held (and after release), serves ACCESS-ATTEMPT requests posted by the
    supervisor, so the durable isolation boundary can be proven ON THIS WORKER
    (its own raw OS evidence), not on the Q3 probe.

Protocol (files in --work-dir):
  · on start it writes  .afterglow_worker_ready  containing its pid;
  · it polls            .afterglow_release       for the release token;
  · it polls            .afterglow_access_request.json  {op,path} and answers via
                         .afterglow_access_response.json {result: DENIED|GRANTED|...};
  · it exits when        .afterglow_stop         appears (or on termination).

This file is INTEGRATION-layer test scaffolding; it is NOT a frozen role.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _attempt_read(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            fh.read()
        return "GRANTED"
    except PermissionError:
        return "DENIED"
    except FileNotFoundError:
        return "MISSING"
    except IsADirectoryError:
        return "ISDIR"
    except OSError as e:
        return f"ERROR:{type(e).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default=os.getcwd())
    ap.add_argument("--holding", action="store_true")
    ap.add_argument("--release-token", default="")
    args = ap.parse_args()

    work = Path(args.work_dir).resolve()
    ready = work / ".afterglow_worker_ready"
    release = work / ".afterglow_release"
    stop = work / ".afterglow_stop"
    req = work / ".afterglow_access_request.json"
    resp = work / ".afterglow_access_response.json"

    ready.write_text(str(os.getpid()), encoding="ascii")
    sys.stdout.write("READY_HOLDING\n")
    sys.stdout.flush()

    released = not args.holding
    processing = False
    while True:
        if stop.exists():
            break
        if not released and release.exists():
            try:
                tok = release.read_text(encoding="ascii").strip()
            except OSError:
                tok = ""
            if tok and tok == args.release_token:
                released = True
                processing = True
                sys.stdout.write("RELEASED_INTO_EXECUTION\n")
                sys.stdout.flush()
        # serve an access attempt regardless of released state (isolation must hold
        # both while holding and while executing)
        if req.exists():
            try:
                body = json.loads(req.read_text(encoding="utf-8"))
                target = body.get("path", "")
                verdict = _attempt_read(target) if target else "NO_TARGET"
                
                resp.write_text(json.dumps({"result": verdict, "pid": os.getpid()}),
                                encoding="utf-8")
            except (OSError, ValueError) as e:
                try:
                    resp.write_text(json.dumps({"result": f"ERROR:{type(e).__name__}"}),
                                    encoding="utf-8")
                except OSError:
                    pass
            finally:
                try:
                    req.unlink()
                except OSError:
                    pass
        time.sleep(0.03)

    sys.stdout.write("STOPPED\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
