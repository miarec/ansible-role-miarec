## Summary

Configure SIP over TLS on the recorder's SIPREC interface, optionally with client certificates (mutual TLS). When TLS is on, the role creates a self-signed certificate for the recorder, unless the operator provides one, so that the recorder never creates a certificate of its own.

---

## Purpose

The recorder accepts SIPREC sessions over TLS with the `PortTLS`, `SSLCertificate`, `SSLPrivateKey`, and `SSLCACertificates` settings of `[Protocol::SIPREC]` in `miarec.ini`. Until now, the role set none of them.

When `SSLCertificate` and `SSLPrivateKey` name files that don't exist, the recorder creates a self-signed certificate of its own at startup. A client that verifies or pins the recorder's certificate, such as an SBC in front of the recorders, can't know that certificate before the recorder starts, and the certificate changes whenever its files are lost. Where a compliance requirement asks for mutual TLS, the recorders must also accept only the clients' certificates.

With this change:

* `miarec_siprec_tls_port` sets `PortTLS`. The default, `0`, keeps TLS off. The role always writes `PortTLS`, so that `0` turns TLS off on a host where it was on.
* `miarec_siprec_tls_cert_file` and `miarec_siprec_tls_key_file` set `SSLCertificate` and `SSLPrivateKey`. Preflight fails when TLS is on and either path is empty.
* `miarec_siprec_tls_ca_file` sets `SSLCACertificates`. When it's set, the recorder requires a client certificate signed by one of its CAs. Preflight fails when the file doesn't exist on the host.
* When TLS is on and neither the certificate nor the key exists, `tasks/siprec_tls.yml` creates a self-signed certificate with `openssl req -x509`: RSA 2048, SHA-256, `miarec_siprec_tls_cert_days` days (default 3650), CN and `DNS:` subject alternative name `miarec_siprec_tls_cert_common_name` (default `inventory_hostname`), and the extensions `basicConstraints=critical,CA:FALSE`, `keyUsage=critical,digitalSignature,keyEncipherment`, `extendedKeyUsage=serverAuth`, and `subjectKeyIdentifier=hash`.
* The role never overwrites an existing certificate or key. If only one of the two exists, it fails with a message that names both files, instead of creating a key that doesn't match the certificate.
* openssl writes the key before it can fail, for example, on a common name longer than 64 characters. The role creates both files in a temporary directory and copies them into place with `force: false`, so that a failure leaves no single file behind.
* The key gets owner `root`, group `miarec_bin_group`, and mode `0640`, and the certificate mode `0644`. The existing "Set group ownership on TLS key files" tasks now cover the SIPREC key and its directory too, and a new task sets the group of the certificate.
* The README documents the variables, the self-signed certificate, client certificates, and that recorder settings in the MiaRec database take precedence over `miarec.ini`.

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran molecule tests
* Notes: The `tls` scenario now turns on SIPREC TLS on port 5081 with a client CA, and lets the role create the recorder's certificate in a directory that doesn't exist yet. `prepare.yml` (`tasks/siprec_certificates.yml`) creates the client CA and a client certificate that it signs.
  - New testinfra tests (`molecule/tls/tests/test_siprec_tls.py`):
    - The certificate directory is `root:miarec` 0750, the certificate `root:miarec` 0644, and the key `root:miarec` 0640.
    - The certificate is self-signed, with the subject `CN=<inventory_hostname>` and the SAN `DNS:<inventory_hostname>`, valid for exactly 3650 days, with an RSA 2048 key, a SHA-256 signature, and the extensions above. The key matches the certificate.
    - `[Protocol::SIPREC]` in `miarec.ini` has the four settings.
    - The recorder listens on port 5081, and an `openssl s_client` handshake presents the certificate file.
    - SIP OPTIONS over TLS, with `s_client` trusting only the recorder's certificate and checking its host name: with a client certificate of the client CA, the recorder answers `SIP/2.0 200 OK`. Without a client certificate, the recorder sends the alert `certificate required`. With a client certificate of another CA, it sends `unknown ca`. With TLS 1.3, the server checks the client certificate after the client ends its handshake, so a handshake alone succeeds from the client's point of view. The tests send a request and read the response instead.
  - `converge.yml` also runs `tasks/siprec_tls.yml` with an existing certificate and key and checks that their checksums don't change, and with a certificate without a key and checks that the role fails and creates no key.
  - The `tls` scenario now runs the idempotence step. The second converge reports no change, so it doesn't create the certificate again.
  - The `default` scenario checks that TLS is off: `PortTLS` is `0`, and the three file settings are empty.
  - I checked that the mutual TLS tests can fail: with `SSLCACertificates` emptied in the container's `miarec.ini` and the recorder restarted, the tests of the client without a certificate and the client of another CA fail.
  - `uv run molecule test -s tls` passes on `ubuntu2404`, `ubuntu2204`, `rockylinux9`, and `rhel9`. `uv run molecule test -s default` and `-s sftp` pass on `ubuntu2404`.
  - `ansible-lint` passes.
  - The `converge` and `idempotence` output shows a red `fatal:` line with the message "Only one of the SIPREC TLS certificate ... exists". It comes from the check of a certificate without a key, which expects the failure and rescues it.

---

## Related Issues

Closes #11

---

## Changes

Brief list of main changes:

* Added the variables `miarec_siprec_tls_port`, `miarec_siprec_tls_cert_file`, `miarec_siprec_tls_key_file`, `miarec_siprec_tls_ca_file`, `miarec_siprec_tls_cert_common_name`, and `miarec_siprec_tls_cert_days` to `defaults/main.yml`.
* Added `tasks/siprec_tls.yml`, which creates the self-signed certificate. `tasks/main.yml` imports it after it creates the user and group, when TLS is on.
* Extended the TLS key permission tasks in `tasks/main.yml` with the SIPREC key, and added a task for the group of the certificate.
* Added the `[Protocol::SIPREC]` settings to `tasks/install.yml`, and the SIPREC TLS checks to `tasks/preflight.yml`.
* Extended the `tls` Molecule scenario, and added a check to the `default` scenario.
* CI runs the `tls` scenario next to `default` and `sftp` on every distro.
* Documented the variables in `README.md`, and the scenario in `molecule/README.md`.

---

## Notes for Reviewers

* TLS is off by default, so existing hosts don't change, except that the role now writes `PortTLS = 0` in the format of `ini_file`. The tarball has `PortTLS=0`, so the first run reports a change and restarts the recorder.
* Recorder settings that the web application stores in the database take precedence over `miarec.ini`. If the web application sets any of these settings for a recorder, the role's value has no effect.
* No earlier change says why CI skipped the `tls` scenario. It passes locally on all four distros in the matrix, so this PR adds it. It adds four jobs to each CI run.
* The open PR #9 changes the same TLS tasks in `tasks/main.yml` and `tasks/preflight.yml`, and the `tls` scenario. Whichever merges second needs a rebase.
* Molecule finds the role by the name of the checkout's directory, `ansible-role-miarec`. To run the scenarios from a checkout with another directory name, such as a worktree, add a symbolic link named `ansible-role-miarec` next to it.
