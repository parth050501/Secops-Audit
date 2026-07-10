"""
CodeCore Windows Agent — main entry point.

Runs the read-only PowerShell compliance assessment locally and submits the raw
JSON result to the collector (CCE), which relays it to the platform.

  --once     run once and exit (ideal for Task Scheduler)
  (default)  loop on SCAN_INTERVAL seconds (default daily)
"""
import logging
import sys
import os
import time
import json
import subprocess
import argparse

from .config import load_config, load_state, save_state, VERSION
from .collector_client import CollectorClient, CollectorUnreachable, CollectorAuthError

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("agent")

DEFAULT_SCAN_INTERVAL = 86400


def run_powershell_assessment(script_path: str) -> dict:
    """Run secops-win-assess.ps1 and return its parsed JSON output."""
    if not os.path.exists(script_path):
        raise RuntimeError(f"PowerShell assessment script not found: {script_path}")
    proc = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"assessment failed (rc={proc.returncode}): {proc.stderr[:300]}")
    try:
        return json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"could not parse assessment output: {e}")


def _ensure_enrolled(cfg, client) -> str:
    state = load_state()
    token = state.get("agent_token")
    if token:
        return token
    log.info("Enrolling agent '%s' with collector at %s …", cfg.agent_name, cfg.collector_url)
    token = client.enroll(cfg.agent_name, "windows_server", cfg.enroll_secret)
    save_state({"agent_token": token, "agent_name": cfg.agent_name})
    log.info("Enrolled. Agent token stored.")
    return token


def _scan_and_submit(cfg, client, token):
    log.info("Running Windows assessment…")
    data = run_powershell_assessment(cfg.ps_script)
    client.submit(token, "windows_server", data,
                  target=cfg.agent_name, framework=cfg.framework or None)
    log.info("Windows assessment submitted to collector.")


def run(once: bool):
    cfg = load_config()
    log.info("CodeCore Windows Agent v%s starting", VERSION)
    log.info("Collector: %s | agent: %s", cfg.collector_url, cfg.agent_name)
    client = CollectorClient(cfg.collector_url, verify_tls=cfg.verify_tls, version=VERSION)

    backoff = 5
    token = None
    while token is None:
        try:
            token = _ensure_enrolled(cfg, client)
        except CollectorAuthError:
            log.error("Enroll secret rejected. Check ENROLL_SECRET.")
            sys.exit(2)
        except CollectorUnreachable as e:
            log.warning("Collector not reachable (%s); retrying in %ss…", e, backoff)
            time.sleep(backoff); backoff = min(backoff*2, 120)

    if once:
        try:
            _scan_and_submit(cfg, client, token)
        except CollectorAuthError:
            save_state({}); raise
        log.info("One-shot run complete.")
        return

    interval = int(os.environ.get("SCAN_INTERVAL", DEFAULT_SCAN_INTERVAL))
    while True:
        try:
            _scan_and_submit(cfg, client, token)
        except CollectorAuthError:
            save_state({}); token = _ensure_enrolled(cfg, client)
        except Exception as e:
            log.error("scan cycle error: %s", e)
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description="CodeCore Windows Agent")
    ap.add_argument("--once", action="store_true", help="run once and exit")
    args = ap.parse_args()
    run(once=args.once)


if __name__ == "__main__":
    main()
