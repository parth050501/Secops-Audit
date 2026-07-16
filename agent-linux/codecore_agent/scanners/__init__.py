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


# ── MySQL / MariaDB (a DB on/reachable from this host) ──────────────
@register("mysql")
def scan_mysql(target=None, **kw):
    """Collect read-only MySQL/MariaDB settings into the platform's expected doc.

    Connection details from env:
      MYSQL_HOST (default localhost), MYSQL_PORT (3306), MYSQL_USER,
      MYSQL_PASSWORD, MYSQL_DATABASE (optional)
    Uses a read-only account; only reads SHOW VARIABLES and mysql.user metadata.
    Requires PyMySQL available to the agent (pip install pymysql).
    """
    try:
        import pymysql
    except ImportError:
        raise RuntimeError("pymysql not installed; cannot scan mysql. "
                           "pip install pymysql in the agent environment.")

    host = os.environ.get("MYSQL_HOST", target or "localhost")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    database = os.environ.get("MYSQL_DATABASE") or None

    conn = pymysql.connect(host=host, port=port, user=user, password=password,
                           database=database, connect_timeout=15, read_timeout=30)
    try:
        cur = conn.cursor()

        def var(name):
            cur.execute("SHOW GLOBAL VARIABLES LIKE %s", (name,))
            row = cur.fetchone()
            return row[1] if row else None

        settings = {
            "require_secure_transport": var("require_secure_transport"),
            "have_ssl": var("have_ssl"),
            "general_log": var("general_log"),
            "local_infile": var("local_infile"),
            "skip_name_resolve": var("skip_name_resolve"),
            "default_authentication_plugin": var("default_authentication_plugin"),
        }
        version = var("version")

        # Account hygiene (read-only queries on mysql.user)
        no_pw = wildcard = anon = 0
        try:
            cur.execute("SELECT COUNT(*) FROM mysql.user WHERE authentication_string='' AND plugin IN ('mysql_native_password','')")
            no_pw = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM mysql.user WHERE host='%'")
            wildcard = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM mysql.user WHERE user=''")
            anon = cur.fetchone()[0]
        except Exception:
            pass  # not permitted to read mysql.user; leave zeros

        return {"system_type": "mysql", "raw_data": {
            "version": version, "settings": settings,
            "users_with_no_password": no_pw,
            "users_with_wildcard_host": wildcard,
            "anonymous_users": anon,
        }}
    finally:
        conn.close()


# ── Microsoft SQL Server (a DB reachable from this host) ────────────
@register("mssql")
def scan_mssql(target=None, **kw):
    """Collect read-only SQL Server settings into the platform's expected doc.

    Connection details from env:
      MSSQL_HOST (default localhost), MSSQL_PORT (1433), MSSQL_USER,
      MSSQL_PASSWORD, MSSQL_DATABASE (default master)
    Uses a read-only login; reads sys.configurations and server properties.
    Requires pymssql available to the agent (pip install pymssql).
    """
    try:
        import pymssql
    except ImportError:
        raise RuntimeError("pymssql not installed; cannot scan mssql. "
                           "pip install pymssql in the agent environment.")

    host = os.environ.get("MSSQL_HOST", target or "localhost")
    port = os.environ.get("MSSQL_PORT", "1433")
    user = os.environ.get("MSSQL_USER", "sa")
    password = os.environ.get("MSSQL_PASSWORD", "")
    database = os.environ.get("MSSQL_DATABASE", "master")

    conn = pymssql.connect(server=host, port=port, user=user, password=password,
                           database=database, timeout=30, login_timeout=15)
    try:
        cur = conn.cursor()

        def config_value(name):
            cur.execute("SELECT value_in_use FROM sys.configurations WHERE name=%s", (name,))
            row = cur.fetchone()
            return int(row[0]) if row else None

        settings = {}
        for cfg_name, key in [
            ("xp_cmdshell", "xp_cmdshell"),
            ("Ole Automation Procedures", "ole_automation_procedures"),
            ("clr enabled", "clr_enabled"),
            ("cross db ownership chaining", "cross_db_ownership_chaining"),
            ("remote admin connections", "remote_admin_connections"),
        ]:
            try:
                settings[key] = config_value(cfg_name)
            except Exception:
                settings[key] = None

        # sa account state
        sa_enabled = sa_renamed = None
        try:
            cur.execute("SELECT name, is_disabled FROM sys.server_principals WHERE sid=0x01")
            row = cur.fetchone()
            if row:
                sa_enabled = (row[1] == 0)
                sa_renamed = (row[0].lower() != "sa")
        except Exception:
            pass

        # authentication mode (1 = Windows only, 0 = Mixed)
        auth_mode = None
        try:
            cur.execute("SELECT SERVERPROPERTY('IsIntegratedSecurityOnly')")
            v = cur.fetchone()[0]
            auth_mode = "windows" if int(v) == 1 else "mixed"
        except Exception:
            pass

        # databases without TDE (encryption_state 3 = encrypted)
        dbs_without_tde = None
        try:
            cur.execute("""SELECT COUNT(*) FROM sys.databases d
                           LEFT JOIN sys.dm_database_encryption_keys k ON d.database_id=k.database_id
                           WHERE d.database_id>4 AND (k.encryption_state IS NULL OR k.encryption_state<>3)""")
            dbs_without_tde = cur.fetchone()[0]
        except Exception:
            pass

        version = None
        try:
            cur.execute("SELECT SERVERPROPERTY('ProductVersion')")
            version = str(cur.fetchone()[0])
        except Exception:
            pass

        data = {"version": version, "settings": settings}
        if sa_enabled is not None: data["sa_account_enabled"] = sa_enabled
        if sa_renamed is not None: data["sa_account_renamed"] = sa_renamed
        if auth_mode: data["authentication_mode"] = auth_mode
        if dbs_without_tde is not None: data["databases_without_tde"] = dbs_without_tde

        return {"system_type": "mssql", "raw_data": data}
    finally:
        conn.close()
