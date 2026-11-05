## Summary

Configure SIP over TLS on the recorder's SIPREC interface, optionally with client certificates (mutual TLS). The operator provides the recorder's certificate and key, signed by the CA of the deployment, and the role uploads them from the Ansible control machine, as it uploads the PostgreSQL and Redis client files since #9.

---

## Purpose

The recorder accepts SIPREC sessions over TLS with the `PortTLS`, `SSLCertificate`, `SSLPrivateKey`, and `SSLCACertificates` settings of `[Protocol::SIPREC]` in `miarec.ini`. Until now, the role set none of them.

When `SSLCertificate` and `SSLPrivateKey` name files that don't exist, the recorder creates a self-signed certificate of its own at startup. A client that verifies or pins the recorder's certificate, such as an SBC in front of the recorders, can't know that certificate before the recorder starts, and the certificate changes whenever its files are lost. Where a compliance requirement asks for mutual TLS, the recorders must also accept only the clients' certificates.

With this change:

* `miarec_siprec_tls_port` sets `PortTLS`. The default, `0`, keeps TLS off. The role always writes `PortTLS`, so that `0` turns TLS off on a host where it was on.
* `miarec_siprec_tls_cert_file` and `miarec_siprec_tls_key_file` set `SSLCertificate` and `SSLPrivateKey`. Preflight fails when TLS is on and either path is empty.
* `miarec_siprec_tls_ca_file` sets `SSLCACertificates`. When it's set, the recorder requires a client certificate signed by one of its CAs.
* `miarec_siprec_tls_cert_file_src`, `miarec_siprec_tls_key_file_src`, and `miarec_siprec_tls_ca_file_src` are local copies of the three files. When one is set, `tasks/tls_upload.yml` uploads the file to its `miarec_siprec_tls_*_file` path with owner `root`, group `miarec_bin_group`, mode `0644` for the certificate and the CA and `0640` for the key, creates a missing directory as `0755 root`, and restarts the recorder when the file changed. The SIPREC files join the list of the PostgreSQL and Redis files, so the rules of #13 apply to them: the role sets permissions only on the files it uploads, and leaves an existing directory alone.
* `tasks/tls_verify.yml` checks the SIPREC files too: before the release is unpacked, `miarec_bin_user` must be able to read the certificate, the key, and the CA, uploaded or not. It also fails when TLS is on and the certificate or the key path is empty. The role never creates a certificate.
* The README documents the variables, the upload, the readability check, client certificates, and that recorder settings in the MiaRec database take precedence over `miarec.ini`.

### Why the role doesn't create a certificate

An earlier version of this PR created a self-signed certificate with `openssl req -x509` when neither file existed on the host, and expected the operator to put their own files on the host before the role ran. Both decisions are undone here. A role that deploys an application doesn't make or sign certificates: the operator provides them from the CA of the deployment, as the role takes the PostgreSQL and Redis client certificates. A self-signed certificate is of no use to a client that verifies the recorder against that CA. And files that the operator puts on the host outside the role don't restart the recorder when they change, so a renewed certificate needs a restart from outside the role too. #9 solved both for the PostgreSQL and Redis files with the `*_src` variables, and the SIPREC files work the same way.

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran molecule tests
* Notes: The `tls` scenario turns on SIPREC TLS on port 5081 with client certificates. The `localhost` play of `prepare.yml` (`tasks/siprec_certificates.yml`) generates SIPREC-CA, which stands for the CA of a deployment, and with it the recorder's certificate for `localhost` (`tasks/siprec_recorder_certificate.yml`) and a client certificate, in the Molecule ephemeral directory, as #13 generates the PostgreSQL and Redis certificates. `converge.yml` gives the recorder's certificate and key and the CA certificate to the role as `miarec_siprec_tls_*_src`, so that a passing scenario proves the upload. The CA key never reaches the target. The target play of `prepare.yml` uploads the client certificate for the tests, outside the role's directory.
  - `side_effect.yml` renews the recorder's certificate and key on the control machine, signed by SIPREC-CA, runs the role again, and asserts that the host has the renewed files and that the recorder's main PID changed.
  - testinfra tests (`molecule/tls/tests/test_siprec_tls.py`):
    - The role created the directory `/etc/miarec/tls/siprec` as `root` 0755, the certificate and the CA `root` 0644, and the key `root:miarec` 0640, their content equals the files on the control machine, the CA key isn't on the host, and the `miarec` user reads the key through `runuser`.
    - `[Protocol::SIPREC]` in `miarec.ini` has the four settings.
    - The recorder listens on port 5081, and an `openssl s_client` handshake presents the renewed certificate, which differs from the first one.
    - SIP OPTIONS over TLS, with `s_client` verifying the recorder against SIPREC-CA and checking its host name: with a client certificate of SIPREC-CA, the recorder answers `SIP/2.0 200 OK`. Without a client certificate, the recorder sends the alert `certificate required`. With a client certificate of another CA (the PostgreSQL client certificate of Test-CA-postgresql, which the role uploads), it sends `unknown ca`. With TLS 1.3, the server checks the client certificate after the client ends its handshake, so a handshake alone succeeds from the client's point of view. The tests send a request and read the response instead.
  - The `tls` scenario runs the idempotence step before `side_effect`: the second converge reports no change.
  - The `default` scenario checks that TLS is off: `PortTLS` is `0`, and the three file settings are empty.
  - The sequence `destroy, create, prepare, converge, idempotence, side_effect, verify, destroy` of the `tls` scenario passes with `uv run molecule test -s tls` on:
    - `ubuntu2404`, `ubuntu2204`, `rockylinux9`, and `rhel9`: 20 testinfra tests pass on each, the 10 of `test_tls.py` and the 10 of `test_siprec_tls.py`.
  - `uv run molecule test -s default` passes on `ubuntu2404`.
  - `ansible-lint` and `yamllint .` pass on the files of this PR. In a checkout whose directory isn't named `ansible-role-miarec`, such as a worktree, it also reports that `molecule/sftp/converge.yml` loads the role by name; `master` has the same, and CI checks out the repository under its name.

---

## Related Issues

Closes #11

---

## Changes

Brief list of main changes:

* Added the variables `miarec_siprec_tls_port`, `miarec_siprec_tls_cert_file`, `miarec_siprec_tls_key_file`, `miarec_siprec_tls_ca_file`, and their `*_src` counterparts to `defaults/main.yml`.
* Added the SIPREC files to the upload list of `tasks/tls_upload.yml` and to the readability check of `tasks/tls_verify.yml`, which also fails on an empty certificate or key path, and run both also when the SIPREC port is on (`tasks/main.yml`).
* Added the `[Protocol::SIPREC]` settings to `tasks/install.yml`.
* Extended the `tls` Molecule scenario with the SIPREC certificates, the upload, and the renewal (`side_effect.yml`), and added a check to the `default` scenario.
* CI runs the `tls` scenario next to `default` and `sftp` on every distro.
* Documented the variables in `README.md`, and the scenario in `molecule/README.md`.

---

## Notes for Reviewers

* TLS is off by default, so existing hosts don't change, except that the role now writes `PortTLS = 0` in the format of `ini_file`. The tarball has `PortTLS=0`, so the first run reports a change and restarts the recorder.
* Recorder settings that the web application stores in the database take precedence over `miarec.ini`. If the web application sets any of these settings for a recorder, the role's value has no effect.
* No earlier change says why CI skipped the `tls` scenario. It passes locally on all four distros in the matrix, so this PR adds it. It adds four jobs to each CI run.
* The branch merges `master` after #9 and #13, which changed the same TLS tasks and the `tls` scenario. An earlier version of this branch extended the permission tasks of `tasks/main.yml` with the SIPREC key and checked the files in `tasks/preflight.yml`; both are gone with #13, and the SIPREC files follow its rules instead.
