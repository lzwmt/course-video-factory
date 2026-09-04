#!/usr/bin/env python3
"""Remote delivery (scp/rsync) and webhook notifications after QA."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "config" / "delivery.json"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), "")
    return ENV_PATTERN.sub(repl, value)


def load_delivery_config(path: Path | None = None) -> dict:
    cfg_path = path or CONFIG_PATH
    if not cfg_path.exists():
        return {"targets": {}, "webhooks": []}
    raw = cfg_path.read_text(encoding="utf-8")
    data = json.loads(expand_env(raw))
    return data if isinstance(data, dict) else {"targets": {}, "webhooks": []}


def _print_ok(msg: str) -> None:
    print(f"{GREEN}[SYNC] {msg}{RESET}")


def _print_fail(msg: str) -> None:
    print(f"{RED}[SYNC] {msg}{RESET}")


def sync_target(
    local_path: Path,
    target_name: str = "mac",
    config: dict | None = None,
    remote_name: str | None = None,
) -> bool:
    cfg = config or load_delivery_config()
    targets = cfg.get("targets") or {}
    target = targets.get(target_name)
    if not target:
        _print_fail(f"unknown target '{target_name}'")
        return False
    local_path = Path(local_path)
    if not local_path.exists():
        _print_fail(f"local path missing: {local_path}")
        return False

    kind = str(target.get("type") or "scp").lower()
    dest_name = remote_name or local_path.name
    try:
        if kind == "rsync":
            destination = str(target.get("destination") or "").rstrip("/") + "/"
            if local_path.is_dir():
                cmd = ["rsync", "-av", str(local_path) + "/", destination]
            else:
                cmd = ["rsync", "-av", str(local_path), destination]
            subprocess.run(cmd, check=True)
            _print_ok(f"rsync {local_path} -> {destination}")
            return True

        host = target.get("host") or target_name
        remote_dir = str(target.get("remote_dir") or "~/Downloads/").rstrip("/") + "/"
        remote = f"{host}:{remote_dir}{dest_name}"
        cmd = ["scp"]
        if local_path.is_dir():
            cmd.append("-r")
        cmd += [str(local_path), remote]
        subprocess.run(cmd, check=True)
        _print_ok(f"uploaded {local_path} -> {remote}")
        return True
    except subprocess.CalledProcessError as exc:
        _print_fail(f"{kind} failed ({exc.returncode})")
        return False


def notify_webhooks(
    status: str,
    text: str,
    config: dict | None = None,
    extra: dict | None = None,
) -> list[str]:
    cfg = config or load_delivery_config()
    results: list[str] = []
    for hook in cfg.get("webhooks") or []:
        name = hook.get("name") or "webhook"
        url = str(hook.get("url") or "").strip()
        notify_on = hook.get("notify_on") or ["pass", "fail"]
        if status not in notify_on:
            continue
        if not url:
            results.append(f"{name}: skipped (empty url)")
            continue
        payload = {"msg_type": "text", "content": {"text": text}}
        if extra:
            payload["extra"] = extra
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                results.append(f"{name}: {resp.status}")
        except urllib.error.URLError as exc:
            results.append(f"{name}: error {exc}")
        except Exception as exc:  # noqa: BLE001
            results.append(f"{name}: error {exc}")
    return results


def deliver_after_qa(
    final_mp4: Path,
    passed: bool,
    reports: list[str] | None = None,
    sync: bool = False,
    sync_target_name: str | None = None,
    remote_name: str | None = None,
    config: dict | None = None,
) -> dict:
    cfg = config or load_delivery_config()
    status = "pass" if passed else "fail"
    reports = reports or []
    headline = f"HyperFrames QA {'PASS' if passed else 'FAIL'}: {final_mp4}"
    body = headline + "\n" + "\n".join(reports)
    hook_results = notify_webhooks(status, body, config=cfg, extra={"file": str(final_mp4), "status": status})

    synced = False
    target_name = sync_target_name or "mac"
    should_sync = bool(sync)
    if should_sync and passed:
        synced = sync_target(final_mp4, target_name=target_name, config=cfg, remote_name=remote_name)
    elif should_sync and not passed:
        _print_fail("QA did not pass; skip upload")

    return {"status": status, "synced": synced, "webhooks": hook_results}


def main() -> None:
    parser = argparse.ArgumentParser(description="SCP/Rsync delivery + webhook notify")
    parser.add_argument("--target", default="mac")
    parser.add_argument("--file", help="Local file to upload")
    parser.add_argument("--dir", help="Local directory to upload")
    parser.add_argument("--name", help="Remote file name")
    parser.add_argument("--notify", help="Webhook text (optional)")
    parser.add_argument("--status", default="pass", choices=["pass", "fail"])
    args = parser.parse_args()

    cfg = load_delivery_config()
    local = Path(args.file) if args.file else (Path(args.dir) if args.dir else None)
    if local:
        sync_target(local, target_name=args.target, config=cfg, remote_name=args.name)
    if args.notify:
        for line in notify_webhooks(args.status, args.notify, config=cfg):
            print(f"[HOOK] {line}")


if __name__ == "__main__":
    main()
