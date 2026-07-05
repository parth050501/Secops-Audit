"""
Scanners for the Linux agent.

Each scanner runs locally (read-only) and returns:
    {"system_type": <type>, "raw_data": <str|dict>}
matching what the platform parser for that type expects. The agent ships this
raw output to the collector; the platform does the parsing/mapping.

Included:
  - linux    : OpenSCAP (oscap) XCCDF evaluation -> results XML
  - postgres : read-only settings collection from a Postgres on/reachable from
               this host -> settings document (dict)

Registering more scanners is the plug-in point; add @register("type").
"""
import logging
import subprocess
import os
import glob
import tempfile

log = logging.getLogger("agent.scanners")

_REGISTRY = {}


def register(system_type):
    def deco(fn):
        _REGISTRY[system_type] = fn
        return fn
    return deco


def get_scanner(system_type):
    return _REGISTRY.get(system_type)


def available():
    return sorted(_REGISTRY.keys())


# ── Linux via OpenSCAP ──────────────────────────────────────────────
@register("linux")
def scan_linux(target=None, profile=None, datastream=None, **kw):
    """Run oscap xccdf eval and return the results XML.

    Requires the `oscap` tool and SCAP content (scap-security-guide) installed
    on the host. profile/datastream can be set via env (OSCAP_PROFILE,
    OSCAP_DATASTREAM) for the specific benchmark you want.
    """
    ds = datastream or os.environ.get("OSCAP_DATASTREAM")
    if not ds:
        candidates = sorted(glob.glob("/usr/share/xml/scap/ssg/content/ssg-*-ds.xml"))
        ds = candidates[0] if candidates else None
    if not ds or not os.path.exists(ds):
        raise RuntimeError(
            "No SCAP datastream found. Install scap-security-guide (provides "
            "/usr/share/xml/scap/ssg/content/ssg-*-ds.xml) or set OSCAP_DATASTREAM."
        )
    profile = profile or os.environ.get("OSCAP_PROFILE")  # e.g. xccdf_org.ssgproject.content_profile_cis
    out_dir = tempfile.mkdtemp(prefix="oscap_")
    results = os.path.join(out_dir, "results.xml")
    cmd = ["oscap", "xccdf", "eval", "--results", results]
    if profile:
        cmd += ["--profile", profile]
    cmd += [ds]
    log.info("Running: %s", " ".join(cmd))
    # oscap returns 2 when some rules fail — that's normal, not an execution error
    proc = subprocess.run(cmd, capture_output=True, timeout=3600, text=True)
    if not os.path.exists(results):
        raise RuntimeError(f"oscap produced no results (rc={proc.returncode}): {proc.stderr[:300]}")
    with open(results) as f:
        return {"system_type": "linux", "raw_data": f.read()}


# ── PostgreSQL (a DB on/reachable from this host) ───────────────────
@register("postgres")
def scan_postgres(target=None, **kw):
    """Collect read-only Postgres settings into the platform's expected document.

    Connection details from env:
      PGHOST (default localhost), PGPORT (5432), PGUSER, PGPASSWORD, PGDATABASE
    Uses a read-only connection and only reads pg_settings / catalog metadata.
    Requires psycopg2 (or psycopg) available to the agent.
    """
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError("psycopg2 not installed; cannot scan postgres. "
                           "pip install psycopg2-binary in the agent environment.")

    host = os.environ.get("PGHOST", target or "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "")
    database = os.environ.get("PGDATABASE", "postgres")

    conn = psycopg2.connect(host=host, port=port, user=user,
                            password=password, dbname=database, connect_timeout=15)
    conn.set_session(readonly=True)
    try:
        cur = conn.cursor()

        def setting(name):
            cur.execute("SELECT setting FROM pg_settings WHERE name=%s", (name,))
            row = cur.fetchone()
            return row[0] if row else None

        settings = {
            "ssl": setting("ssl"),
            "log_connections": setting("log_connections"),
            "log_disconnections": setting("log_disconnections"),
            "logging_collector": setting("logging_collector"),
            "log_statement": setting("log_statement"),
            "password_encryption": setting("password_encryption"),
        }

        # superuser count
        cur.execute("SELECT count(*) FROM pg_roles WHERE rolsuper")
        superuser_count = cur.fetchone()[0]

        # public schema world-writable? (CREATE granted to PUBLIC)
        cur.execute("""
            SELECT has_schema_privilege('public', 'public', 'CREATE')
        """)
        public_writable = bool(cur.fetchone()[0])

        # pg_hba 'trust' detection (needs superuser to read pg_hba_file_rules)
        hba_trust = False
        try:
            cur.execute("SELECT count(*) FROM pg_hba_file_rules WHERE auth_method='trust'")
            hba_trust = cur.fetchone()[0] > 0
        except Exception:
            hba_trust = None  # not readable; leave unknown

        version = setting("server_version")
        data = {
            "version": version,
            "settings": settings,
            "superuser_count": superuser_count,
            "public_schema_world_writable": public_writable,
        }
        if hba_trust is not None:
            data["hba_allows_trust"] = hba_trust
        return {"system_type": "postgres", "raw_data": data}
    finally:
        conn.close()
