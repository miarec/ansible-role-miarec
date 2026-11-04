"""SIP over TLS on the SIPREC interface, with client certificates (mutual TLS).

prepare.yml (tasks/siprec_certificates.yml) creates SIPREC-CA, the CA of the
deployment, and with it the recorder's certificate and a client certificate.
It fetches the recorder's certificate and key, and the CA certificate, to the
control machine, and converge.yml gives them to the role as
miarec_siprec_tls_*_src, which uploads them and turns on TLS on port 5081
with client certificates. side_effect.yml renews the recorder's certificate
on the control machine and runs the role again. The tests connect to the
recorder with `openssl s_client` from inside the container.
"""
import os
import re
import shlex
from pathlib import Path

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

INI = "/opt/miarec/current/miarec.ini"
PORT = 5081
# On the host: what converge.yml gives the role.
CERT_DIR = "/etc/miarec/siprec-tls"
CERT = f"{CERT_DIR}/recorder.crt"
KEY = f"{CERT_DIR}/recorder.key"
CA = f"{CERT_DIR}/ca.crt"
# On the control machine: what the role uploads (prepare.yml, side_effect.yml).
SRC_DIR = Path(os.environ["MOLECULE_EPHEMERAL_DIRECTORY"]) / "tls" / "siprec"
FIRST_CERT_SRC = SRC_DIR / "recorder-first.crt"
CLIENT_CERT = "/etc/miarec/tls/siprec-client.crt"
CLIENT_KEY = "/etc/miarec/tls/siprec-client.key"
# certificates.yml makes this client certificate for PostgreSQL and Redis.
# Test-CA signs it, and the recorder doesn't trust Test-CA for SIPREC.
OTHER_CA_CLIENT_CERT = "/etc/miarec/tls/client.crt"
OTHER_CA_CLIENT_KEY = "/etc/miarec/tls/client.key"
GROUP = os.environ.get("MIAREC_BIN_GROUP", "miarec")


def host_name(host):
    # tasks/siprec_recorder_certificate.yml makes the certificate for the inventory host name.
    return host.ansible.get_variables()["inventory_hostname"]


def siprec_settings(host):
    content = host.file(INI).content_string
    section = re.search(r"^\[Protocol::SIPREC\]\n(.*?)(?=^\[)", content, re.M | re.S)
    assert section, f"{INI} has no [Protocol::SIPREC] section"
    return dict(re.findall(r"^(\w+)\s*=[ \t]*(.*?)[ \t]*$", section.group(1), re.M))


def presented_certificate(host):
    """Return the certificate that the recorder presents in a TLS handshake."""
    result = host.run(
        f"openssl s_client -connect 127.0.0.1:{PORT} "
        f"-cert {CLIENT_CERT} -key {CLIENT_KEY} < /dev/null"
    )
    assert result.rc == 0, result.stdout + result.stderr
    presented = re.search(
        r"^-----BEGIN CERTIFICATE-----\n.*?^-----END CERTIFICATE-----\n", result.stdout, re.M | re.S)
    assert presented, f"s_client printed no server certificate:\n{result.stdout}"
    return presented.group(0)


def sip_options_over_tls(host, cert=None, key=None):
    """Send SIP OPTIONS to the recorder over TLS, and return the result of s_client.

    s_client verifies the recorder's certificate against SIPREC-CA and checks
    its host name, as a client of the deployment does. With TLS 1.3, the
    recorder checks the client certificate after the client ends its
    handshake, and s_client sees the recorder's alert only when it reads. So
    the tests read a response to a request instead of checking the handshake
    alone.
    """
    name = host_name(host)
    request = (
        f"OPTIONS sip:{name}:{PORT};transport=tls SIP/2.0\r\n"
        "Via: SIP/2.0/TLS 127.0.0.1:5061;branch=z9hG4bK-molecule;rport\r\n"
        "Max-Forwards: 70\r\n"
        "From: <sip:molecule@127.0.0.1>;tag=molecule\r\n"
        f"To: <sip:{name}>\r\n"
        "Call-ID: molecule-siprec-tls@127.0.0.1\r\n"
        "CSeq: 1 OPTIONS\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    )
    client = f"-cert {cert} -key {key}" if cert else ""
    # s_client reads until its input ends: the sleep gives the recorder time to answer.
    return host.run(
        f"(printf %s {shlex.quote(request)}; sleep 2) | timeout 15 "
        f"openssl s_client -connect 127.0.0.1:{PORT} -CAfile {CA} "
        f"-verify_hostname {name} -verify_return_error -quiet -no_ign_eof {client}"
    )


def test_the_role_creates_the_directory_and_the_files_with_their_permissions(host):
    directory = host.file(CERT_DIR)
    assert directory.is_directory
    assert (directory.user, directory.group, directory.mode) == ("root", GROUP, 0o750)

    for path in (CERT, CA):
        certificate = host.file(path)
        assert certificate.is_file
        assert (certificate.user, certificate.group, certificate.mode) == ("root", GROUP, 0o644)

    key = host.file(KEY)
    assert key.is_file
    assert (key.user, key.group, key.mode) == ("root", GROUP, 0o640)


def test_the_role_uploads_the_files_from_the_control_machine(host):
    for path, name in ((CERT, "recorder.crt"), (KEY, "recorder.key"), (CA, "ca.crt")):
        assert host.file(path).content_string == (SRC_DIR / name).read_text(), path


def test_miarec_ini_has_the_siprec_tls_settings(host):
    settings = siprec_settings(host)
    assert settings["PortTLS"] == str(PORT)
    assert settings["SSLCertificate"] == CERT
    assert settings["SSLPrivateKey"] == KEY
    assert settings["SSLCACertificates"] == CA


def test_the_recorder_listens_on_the_tls_port(host):
    assert host.socket(f"tcp://0.0.0.0:{PORT}").is_listening


def test_the_recorder_presents_the_renewed_certificate(host):
    """side_effect.yml renewed the certificate on the control machine and ran the role again."""
    renewed = (SRC_DIR / "recorder.crt").read_text()
    assert renewed != FIRST_CERT_SRC.read_text()
    assert host.file(CERT).content_string == renewed
    assert presented_certificate(host) == renewed


def test_the_recorder_answers_a_client_with_a_certificate_of_the_client_ca(host):
    result = sip_options_over_tls(host, CLIENT_CERT, CLIENT_KEY)
    assert result.rc == 0, result.stdout + result.stderr
    assert "SIP/2.0 200 OK\r\n" in result.stdout


def test_the_recorder_refuses_a_client_without_a_certificate(host):
    result = sip_options_over_tls(host)
    assert result.rc != 0
    assert "alert certificate required" in result.stderr
    assert "SIP/2.0" not in result.stdout


def test_the_recorder_refuses_a_client_certificate_of_another_ca(host):
    result = sip_options_over_tls(host, OTHER_CA_CLIENT_CERT, OTHER_CA_CLIENT_KEY)
    assert result.rc != 0
    assert "alert unknown ca" in result.stderr
    assert "SIP/2.0" not in result.stdout
