"""
CodeCore Collector Engine — RELAY.

The collector does NOT scan. Agents (on internal systems) do all scanning and
send raw results to this collector; the collector authenticates them, buffers
results durably, and forwards them to the platform (APE) under its own tenant
binding (its platform token).

Lifecycle:
  1. Load config (APE URL + platform token; agent enroll secret).
  2. Enroll with the APE (heartbeat) — confirms the tenant this collector serves.
  3. Start the inbound agent-facing server (agents enroll + submit results).
  4. Loop: heartbeat to APE on interval; drain the durable queue to the APE;
     on APE outage, keep results and retry (nothing lost).

The token is never logged. All APE traffic is outbound HTTPS. The inbound agent
server listens on the internal network only (never exposed to the internet).
"""
import logging
import time
import signal
import sys

from .config import load_config, VERSION
from .queue import ResultQueue
from .agent_registry import AgentRegistry
from .inbound import start_inbound_server
from .ape_client import ApeClient, ApeUnreachable, ApeAuthError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("collector")

_running = True


def _stop(signum, frame):
    global _running
    log.info("Shutdown signal received; finishing current cycle and exiting.")
    _running = False


def run():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    cfg = load_config()
    log.info("CodeCore Collector (relay) v%s starting", VERSION)
    log.info("APE: %s  | token: %s", cfg.ape_url, cfg.masked_token())

    if not cfg.enroll_secret:
        log.warning("No ENROLL_SECRET set — agents will not be able to enroll. "
                    "Set one so agents can register with this collector.")

    q = ResultQueue(cfg.queue_path)
    registry = AgentRegistry(cfg.agent_db_path)
    client = ApeClient(cfg.ape_url, cfg.token, verify_tls=cfg.verify_tls, version=VERSION)

    # ── Enroll with the APE ──
    backoff = 5
    while _running:
        try:
            resp = client.heartbeat()
            tenant = resp.get("collector") or "(confirmed)"
            log.info("Enrolled and connected to platform. Collecting for: %s", tenant)
            break
        except ApeAuthError:
            log.error("Platform token rejected. Check COLLECTOR_TOKEN and APE_URL.")
            sys.exit(2)
        except ApeUnreachable as e:
            log.warning("Platform not reachable yet (%s). Retrying in %ss…", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)

    # ── Start the inbound agent server (relay receive side) ──
    server = start_inbound_server(
        registry, q, cfg.enroll_secret,
        host=cfg.inbound_host, port=cfg.inbound_port,
    )

    last_heartbeat = time.time()
    # ── Main loop: heartbeat + drain queue to platform ──
    while _running:
        now = time.time()
        if now - last_heartbeat >= cfg.heartbeat_interval:
            try:
                client.heartbeat()
                last_heartbeat = now
            except ApeAuthError:
                log.error("Platform token rejected during heartbeat; stopping.")
                break
            except ApeUnreachable as e:
                log.warning("Heartbeat failed (%s); will retry.", e)

        _drain_queue(q, client)

        slept = 0
        while _running and slept < cfg.poll_interval:
            time.sleep(1)
            slept += 1

    server.shutdown()
    log.info("Collector stopped cleanly. %d result(s) still queued.", q.count())


def _drain_queue(q: ResultQueue, client: ApeClient):
    pending = q.pending()
    if not pending:
        return
    log.info("Forwarding %d queued result(s) to platform…", len(pending))
    for item in pending:
        try:
            client.submit_result(
                item["system_type"], item["raw_data"],
                job_id=item["job_id"], target=item["target"], framework=item["framework"],
            )
            q.mark_uploaded(item["id"])
        except ValueError as e:
            log.warning("Dropping unsendable result %s: %s", item["id"], e)
            q.mark_uploaded(item["id"])
        except ApeUnreachable:
            q.mark_failed(item["id"])
            log.warning("Platform unreachable; keeping result %s for retry.", item["id"])
            break


if __name__ == "__main__":
    run()
