"""Test TLS configuration for MiaRec."""
import json
import os
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

RECORDER_USER = os.environ.get("MIAREC_BIN_USER", "miarec")
RECORDER_GROUP = os.environ.get("MIAREC_BIN_GROUP", "miarec")

# PostgreSQL and Redis each have their own PKI. The role uploads the client
# files into a directory per service.
SERVICES = ("postgresql", "redis")


def test_miarec_service_running(host):
    """Test that miarec service is running."""
    service = host.service('miarec')
    assert service.is_running
    assert service.is_enabled


def test_miarec_runs_as_recorder_user(host):
    """The recorder runs as miarec_bin_user, not as root."""
    recorders = [p for p in host.process.filter(user=RECORDER_USER) if p.comm == "miarec"]
    assert recorders, f"No miarec process runs as user {RECORDER_USER}"
    root_recorders = [p for p in host.process.filter(user="root") if p.comm == "miarec"]
    assert not root_recorders, "A miarec process runs as root"


def test_miarec_ini_has_tls_settings(host):
    """Test that miarec.ini contains TLS settings."""
    ini_file = host.file('/opt/miarec/current/miarec.ini')
    assert ini_file.exists
    content = ini_file.content_string

    # Check PostgreSQL TLS settings
    assert 'UseSSL=true' in content or 'UseSSL = true' in content
    assert 'SSLCACertificates' in content
    assert 'SSLCertificate' in content
    assert 'SSLPrivateKey' in content


def test_tls_certificates_exist(host):
    """Verify TLS certificates were uploaded."""
    cert_files = [
        # CA and client certs per service, uploaded by the role
        *(f"/etc/miarec/tls/{svc}/{name}"
          for svc in SERVICES for name in ("ca.crt", "client.crt", "client.key")),
        # PostgreSQL server certs in /etc/postgresql/tls/, uploaded by prepare
        "/etc/postgresql/tls/server.crt",
        "/etc/postgresql/tls/server.key",
        "/etc/postgresql/tls/ca.crt",
        # Redis server certs in /etc/redis/tls/, uploaded by prepare
        "/etc/redis/tls/server.crt",
        "/etc/redis/tls/server.key",
        "/etc/redis/tls/ca.crt",
    ]
    for cert_file in cert_files:
        f = host.file(cert_file)
        assert f.exists, f"Certificate file not found: {cert_file}"
        assert f.is_file, f"Not a file: {cert_file}"


def test_ca_key_not_on_host(host):
    """The CA private keys stay on the control machine."""
    for svc in SERVICES:
        assert not host.file(f"/etc/miarec/tls/{svc}/ca.key").exists


def test_tls_file_permissions(host):
    """The role uploads the private keys readable by the recorder's group only."""
    for svc in SERVICES:
        key = host.file(f"/etc/miarec/tls/{svc}/client.key")
        assert key.user == "root", f"{svc} key is not owned by root"
        assert key.group == RECORDER_GROUP, f"{svc} key is not group {RECORDER_GROUP}"
        assert key.mode == 0o640, f"{svc} key is not 0640"
        for name in ("ca.crt", "client.crt"):
            cert = host.file(f"/etc/miarec/tls/{svc}/{name}")
            assert cert.user == "root", f"{svc}/{name} is not owned by root"
            assert cert.mode == 0o644, f"{svc}/{name} is not 0644"
        # The role created the directory, so it has the fixed mode, not the umask.
        tls_dir = host.file(f"/etc/miarec/tls/{svc}")
        assert tls_dir.user == "root", f"{svc} directory is not owned by root"
        assert tls_dir.mode == 0o755, f"{svc} directory is not 0755"


def test_recorder_user_can_read_tls_keys(host):
    """The recorder's user reads the private keys through miarec_bin_group."""
    for svc in SERVICES:
        result = host.run(f"runuser -u {RECORDER_USER} -- cat /etc/miarec/tls/{svc}/client.key")
        assert result.rc == 0, f"{RECORDER_USER} cannot read {svc} client.key: {result.stderr}"


def test_postgresql_tls_connection(host):
    """Test that PostgreSQL TLS connection works with the uploaded client files."""
    cmd = host.run(
        'psql "host=127.0.0.1 port=5432 dbname=miarecdb user=miarec password=password '
        'sslmode=verify-ca '
        'sslrootcert=/etc/miarec/tls/postgresql/ca.crt '
        'sslcert=/etc/miarec/tls/postgresql/client.crt '
        'sslkey=/etc/miarec/tls/postgresql/client.key" '
        '-c "SELECT 1;"'
    )
    assert cmd.rc == 0, cmd.stderr


def test_redis_tls_connection(host):
    """Test that Redis TLS connection works with the uploaded client files."""
    cmd = host.run(
        'redis-cli --tls '
        '--cacert /etc/miarec/tls/redis/ca.crt '
        '--cert /etc/miarec/tls/redis/client.crt '
        '--key /etc/miarec/tls/redis/client.key '
        '-h 127.0.0.1 -p 6379 PING'
    )
    assert cmd.rc == 0, cmd.stderr
    assert 'PONG' in cmd.stdout


def test_health_endpoint(host):
    """Verify /health endpoint returns healthy status for TLS connections."""
    # MiaRec REST API listens on port 6088
    result = host.run("curl -fsS http://localhost:6088/health")
    assert result.rc == 0, f"Health endpoint not reachable: {result.stderr}"

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Health endpoint response is not valid JSON: {exc}\n"
            f"Response: {result.stdout}"
        )

    assert payload.get("status") == "ok", f"Unexpected overall status: {payload}"
    assert payload.get("database") == "ok", f"Database TLS connection failed: {payload}"
    assert payload.get("redis") == "ok", f"Redis TLS connection failed: {payload}"
