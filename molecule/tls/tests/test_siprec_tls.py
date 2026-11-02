"""SIP over TLS on the SIPREC interface, with client certificates (mutual TLS).

converge.yml turns on TLS on port 5081 with a client CA, and lets the role
create the recorder's self-signed certificate. prepare.yml
(tasks/siprec_certificates.yml) creates the client CA and a client certificate
that it signs. The tests connect to the recorder with `openssl s_client` from
inside the container.

converge.yml also checks that the role keeps an existing certificate and key,
and that it fails on a certificate without a key.
"""
import datetime
import os
import re
import shlex

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

INI = "/opt/miarec/current/miarec.ini"
PORT = 5081
CERT_DIR = "/etc/miarec/siprec-tls"
CERT = f"{CERT_DIR}/recorder.crt"
KEY = f"{CERT_DIR}/recorder.key"
CLIENT_CA = "/etc/miarec/tls/siprec-client-ca.crt"
CLIENT_CERT = "/etc/miarec/tls/siprec-client.crt"
CLIENT_KEY = "/etc/miarec/tls/siprec-client.key"
# certificates.yml makes this client certificate for PostgreSQL and Redis.
# Test-CA signs it, and the recorder doesn't trust Test-CA for SIPREC.
OTHER_CA_CLIENT_CERT = "/etc/miarec/tls/client.crt"
OTHER_CA_CLIENT_KEY = "/etc/miarec/tls/client.key"
GROUP = os.environ.get("MIAREC_BIN_GROUP", "miarec")
# miarec_siprec_tls_cert_days in defaults/main.yml
CERT_DAYS = 3650


def common_name(host):
    # miarec_siprec_tls_cert_common_name defaults to the inventory hostname.
    return host.ansible.get_variables()["inventory_hostname"]


def x509(host, *options):
    result = host.run(f"openssl x509 -in {CERT} -noout {' '.join(options)}")
    assert result.rc == 0, result.stderr
    return result.stdout


def siprec_settings(host):
    content = host.file(INI).content_string
    section = re.search(r"^\[Protocol::SIPREC\]\n(.*?)(?=^\[)", content, re.M | re.S)
    assert section, f"{INI} has no [Protocol::SIPREC] section"
    return dict(re.findall(r"^(\w+)\s*=[ \t]*(.*?)[ \t]*$", section.group(1), re.M))


def sip_options_over_tls(host, cert=None, key=None):
    """Send SIP OPTIONS to the recorder over TLS, and return the result of s_client.

    s_client trusts only the recorder's certificate and checks its host name,
    as a client that pins the certificate does. With TLS 1.3, the recorder
    checks the client certificate after the client ends its handshake, and
    s_client sees the recorder's alert only when it reads. So the tests read a
    response to a request instead of checking the handshake alone.
    """
    name = common_name(host)
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
        f"openssl s_client -connect 127.0.0.1:{PORT} -CAfile {CERT} "
        f"-verify_hostname {name} -verify_return_error -quiet -no_ign_eof {client}"
    )


def test_the_role_creates_the_certificate_and_key_files(host):
    # The role creates the missing directory too.
    directory = host.file(CERT_DIR)
    assert directory.is_directory
    assert (directory.user, directory.group, directory.mode) == ("root", GROUP, 0o750)

    cert = host.file(CERT)
    assert cert.is_file
    assert (cert.user, cert.group, cert.mode) == ("root", GROUP, 0o644)

    key = host.file(KEY)
    assert key.is_file
    assert (key.user, key.group, key.mode) == ("root", GROUP, 0o640)


def test_the_certificate_is_self_signed_for_the_host_name(host):
    name = common_name(host)
    names = x509(host, "-subject", "-issuer", "-nameopt", "RFC2253").splitlines()
    assert names == [f"subject=CN={name}", f"issuer=CN={name}"]
    assert f"DNS:{name}" in x509(host, "-ext", "subjectAltName")


def test_the_certificate_is_valid_for_the_configured_days(host):
    dates = {
        name: datetime.datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
        for name, value in (
            line.split("=", 1) for line in x509(host, "-startdate", "-enddate").splitlines())
    }
    assert dates["notAfter"] - dates["notBefore"] == datetime.timedelta(days=CERT_DAYS)


def test_the_certificate_has_a_2048_bit_rsa_key_and_server_extensions(host):
    text = x509(host, "-text")
    assert "Public Key Algorithm: rsaEncryption" in text
    assert "Public-Key: (2048 bit)" in text
    assert "Signature Algorithm: sha256WithRSAEncryption" in text

    extensions = re.sub(r"\s+", " ", x509(
        host, "-ext", "basicConstraints,keyUsage,extendedKeyUsage,subjectKeyIdentifier"))
    assert "X509v3 Basic Constraints: critical CA:FALSE" in extensions
    assert "X509v3 Key Usage: critical Digital Signature, Key Encipherment" in extensions
    assert "X509v3 Extended Key Usage: TLS Web Server Authentication" in extensions
    assert "X509v3 Subject Key Identifier:" in extensions


def test_the_key_matches_the_certificate(host):
    key_public = host.run(f"openssl pkey -in {KEY} -pubout")
    assert key_public.rc == 0, key_public.stderr
    assert x509(host, "-pubkey") == key_public.stdout


def test_miarec_ini_has_the_siprec_tls_settings(host):
    settings = siprec_settings(host)
    assert settings["PortTLS"] == str(PORT)
    assert settings["SSLCertificate"] == CERT
    assert settings["SSLPrivateKey"] == KEY
    assert settings["SSLCACertificates"] == CLIENT_CA


def test_the_recorder_listens_on_the_tls_port(host):
    assert host.socket(f"tcp://0.0.0.0:{PORT}").is_listening


def test_the_handshake_presents_the_certificate(host):
    result = host.run(
        f"openssl s_client -connect 127.0.0.1:{PORT} "
        f"-cert {CLIENT_CERT} -key {CLIENT_KEY} < /dev/null"
    )
    assert result.rc == 0, result.stdout + result.stderr
    presented = re.search(
        r"^-----BEGIN CERTIFICATE-----\n.*?^-----END CERTIFICATE-----\n", result.stdout, re.M | re.S)
    assert presented, f"s_client printed no server certificate:\n{result.stdout}"
    assert presented.group(0) == host.file(CERT).content_string


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
