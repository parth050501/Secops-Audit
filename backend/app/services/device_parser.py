"""
Device parser framework.

Turns RAW device config (in the device's native format) into GovernanceEvent
dicts — the same "raw_data → parser → findings" pattern used for agents and
databases. Each device family registers a parser here; adding a new device type
means adding one parser, nothing else changes.

A parser takes (raw_config, tenant_id, device_id, framework_hint) and returns a
list of finding dicts. Until a real parser for a device type is validated against
real hardware, the type simply has no parser and returns an empty list (fail-safe
— never invents findings).

This is deliberately a thin registry so per-device parsers (Palo Alto, Fortinet,
Cisco, …) slot in cleanly and are each validated against real devices.
"""
import logging

log = logging.getLogger("device.parser")

# device_type -> parser callable
_PARSERS = {}


def register_parser(device_type):
    def deco(fn):
        _PARSERS[device_type] = fn
        return fn
    return deco


def has_parser(device_type: str) -> bool:
    return device_type in _PARSERS


def supported_types() -> list:
    return sorted(_PARSERS.keys())


def parse_device_config(device_type: str, raw_config, tenant_id: int,
                        device_id: int, framework_hint: str = None) -> list:
    """Route raw config to the right parser. Returns [] if no parser yet (safe)."""
    parser = _PARSERS.get(device_type)
    if not parser:
        log.info("no parser for device_type '%s' yet; returning no findings", device_type)
        return []
    try:
        return parser(raw_config, tenant_id, device_id, framework_hint)
    except Exception as e:
        log.warning("parser for '%s' failed: %s", device_type, e)
        return []


# ── Per-device parsers register below as they're built + validated. ──
# Example shape (to be implemented against real hardware):
#
# @register_parser("paloalto")
# def parse_paloalto(raw_config, tenant_id, device_id, framework_hint=None):
#     # raw_config is the device's XML API config; assess and return findings
#     ...
#
# The existing Palo Alto scanner will be adapted into a parser here once
# validated against a real device.
