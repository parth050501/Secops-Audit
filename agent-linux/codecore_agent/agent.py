"""
CodeCore Linux Agent — main entry point.

Runs read-only compliance scans locally and submits raw results to the collector
(CCE). The collector relays them to the platform.

Modes:
  --once     run all configured scans once and exit (ideal for cron/systemd timer)
  (default)  run continuously on an interval (SCAN_INTERVAL seconds, default 1 day)

Enrollment happens once: the agent enrolls with the collector using the shared
enroll secret, receives an agent token, and stores it (0600) so subsequent runs
reuse it.
"""
import logging
import sys
import time
import argparse

from .config import load_config, load_state, save_state, VERSION
from .collector_client import CollectorClient, CollectorUnreachable, CollectorAuthError
from . import scanners

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("agent")

DEFAULT_SCAN_INTERVAL = 86400   # once a day


def _ensure_enrolled(cfg, client) -> str:
    """Return a valid agent token, enrolling once if needed."""
    state = load_state()
    token = state.get("agent_token")
    if token:
        return token
    # Enroll. system_type registered is the first configured scan type (label only;
    # the agent can still submit multiple types).
    first_type = cfg.scan_systems.split(",")[0].strip() or "linux"
    log.info("Enrolling agent '%s' with collector at %s …", cfg.agent_name, cfg.collector_url)
    token = client.enroll(cfg.agent_name, first_type, cfg.enroll_secret)
    save_state({"agent_token": token, "agent_name": cfg.agent_name})
    log.info("Enrolled. Agent token stored.")
    return token


def _run_scans(cfg, client, token):
    types = [t.strip() for t in cfg.scan_systems.split(",") if t.strip()]
    for system_type in types:
        scanner = scanners.get_scanner(system_type)
        if not scanner:
            log.warning("No scanner for '%s' (available: %s); skipping.",
                        system_type, scanners.available())
            continue
        try:
            log.info("Running %s scan…", system_type)
            result = scanner()
            client.submit(token, result["system_type"], result["raw_data"],
                          target=cfg.agent_name, framework=cfg.framework or None)
            log.info("%s scan submitted to collector.", system_type)
        except CollectorAuthError:
            # token may have been revoked — clear it so next cycle re-enrolls
            log.error("Collector rejected the agent token; clearing for re-enroll.")
            save_state({})
            raise
        except CollectorUnreachable as e:
            log.warning("Could not submit %s result (collector unreachable): %s", system_type, e)
        except Exception as e:
            log.error("%s scan failed: %s", system_type, e)


def run(once: bool):
    cfg = load_config()
    log.info("CodeCore Linux Agent v%s starting", VERSION)
    log.info("Collector: %s | agent: %s | scans: %s",
             cfg.collector_url, cfg.agent_name, cfg.scan_systems)
    log.info("Scanners available: %s", scanners.available())

    client = CollectorClient(cfg.collector_url, verify_tls=cfg.verify_tls, version=VERSION)

    # Enroll (with retry/backoff if collector not yet reachable)
    backoff = 5
    token = None
    while token is None:
        try:
            token = _ensure_enrolled(cfg, client)
        except CollectorAuthError:
            log.error("Enroll secret rejected by collector. Check ENROLL_SECRET.")
            sys.exit(2)
        except CollectorUnreachable as e:
            log.warning("Collector not reachable (%s); retrying in %ss…", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)

    if once:
        _run_scans(cfg, client, token)
        log.info("One-shot run complete.")
        return

    interval = int(__import__("os").environ.get("SCAN_INTERVAL", DEFAULT_SCAN_INTERVAL))
    log.info("Running on a %ss interval. Ctrl-C to stop.", interval)
    while True:
        try:
            _run_scans(cfg, client, token)
        except CollectorAuthError:
            # re-enroll next loop
            token = _ensure_enrolled(cfg, client)
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description="CodeCore Linux Agent")
    ap.add_argument("--once", action="store_true", help="run scans once and exit")
    args = ap.parse_args()
    run(once=args.once)


if __name__ == "__main__":
    main()
