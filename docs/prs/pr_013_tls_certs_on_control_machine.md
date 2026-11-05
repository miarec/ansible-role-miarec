## Summary

Make the TLS upload touch only the files it uploads, verify that the recorder's user can read every TLS file before the release is unpacked, and generate the TLS test certificates on the control machine so the `tls` Molecule scenario proves the role's upload. Also add a `.yamllint` config that agrees with `.ansible-lint`, and normalize line endings to LF.

This ports the fixes from ansible-role-miarecweb PR 20 to this role.

---

## Purpose

PR 9 made the role upload the TLS files from the control machine. Its `tls` scenario generated every certificate on the target, inside `/etc/miarec/tls`, the directory the role manages. It then fetched the client files to the control machine and deleted them, so the role could upload them again. This had three flaws:

* The fixture created `/etc/miarec/tls` with its own owner and mode, so the test didn't cover the role creating the directory.
* The CA private key and the OpenSSL scratch files stayed in the role's directory on the target. A failed prepare left the client files there too, and converge then passed without an upload.
* The prepare checks that connected to PostgreSQL and Redis with the client certificate needed the client files on the target, which is the opposite of what the role does in production.

With this change, a play on `localhost` generates the CA, the client certificate, and the PostgreSQL and Redis server certificates in the Molecule ephemeral directory. The PostgreSQL and Redis fixtures upload their own server certificate and the CA certificate. Nothing in prepare writes to `/etc/miarec/tls`. The role creates that directory and uploads the client files during converge, the same way the production playbooks do. The CA private key never reaches the target, and verify asserts that.

### Permissions of files the role did not upload

PR 9 kept two tasks from the first TLS commit that set the group and mode on every private key in use and on its directory, whether the role uploaded the key or not. Pointed at a key in a shared directory such as `/etc/ssl/private`, they rewrote the directory and the key from group `ssl-cert` to `miarec_bin_group` and cut other services off from their own keys. The upload task also set `root:miarec_bin_group` and mode 0750 on the parent directory of every uploaded file, which locked a shared directory such as `/etc/ssl/certs` for every other user.

With this change, the role sets permissions only on the files it uploads, in `tasks/tls_upload.yml`. A missing parent directory is created as `0755 root:root`, regardless of the host's umask, and an existing one is left alone. A file that is already on the host, because its `*_src` variable is empty, is left as is.

### Verify the recorder can read the files

A TLS file that the recorder's user cannot read used to surface only when the service restarted, after the play had already upgraded the server. `tasks/tls_verify.yml` runs `test -r` on every TLS file in use as `miarec_bin_user`, through `runuser`, which applies the user's supplementary groups the way systemd does. The check covers directory traversal, the file mode, and the group membership, for files the role uploaded and files that arrived by other means. It runs after the user and group exist and before `deploy_helper` initializes the release, so a failure leaves the host untouched. The preflight checks that only tested whether the files existed are gone with it; a missing file fails in the copy task, which names the missing source, or in the verify step, which names the user and the path.

The group and user tasks in `tasks/main.yml` now run with `become`, like every other task there. They used to work only when the play set `become` itself.

### Lint config and line endings

yamllint had no config in this repo, so it ran with the default rules and reported more than a hundred errors, most of them for rules that `.ansible-lint` already skips. `.yamllint` now mirrors those skips and allows spaces inside braces, so `{ src: ca.crt, mode: "0644" }` passes. It also sets the `comments`, `comments-indentation`, and `octal-values` values that ansible-lint requires. Without them, ansible-lint warns that the config is incompatible and turns off its fix mode.

The systemd unit template was committed with CRLF line endings, so every deploy rendered a CRLF unit file. The template is now LF, and `.gitattributes` keeps it that way on a Windows checkout.

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran molecule tests
* Notes:
  - `uv run molecule test -s tls` passes on Ubuntu 24.04. In converge, the role creates `/etc/miarec/tls/postgresql` and `/etc/miarec/tls/redis`, uploads the six client files, and verifies that the `miarec` user can read them. The testinfra tests pass, including the permission checks, the `runuser` read check, and the TLS connections to PostgreSQL and Redis with the uploaded files.
  - `uv run molecule test -s default` passes on Ubuntu 24.04, which covers `tasks/main.yml` without TLS.
  - `uv run ansible-lint` and `uv run yamllint .` pass without warnings.
  - I didn't run the scenario on the RedHat images locally. The `tls` scenario wasn't in the CI matrix before; it is now, so CI runs it on every distro.

---

## Related Issues

Fixes the Molecule test flaw in #9. Mirrors miarec/ansible-role-miarecweb#20.

---

## Changes

Brief list of main changes:

* `molecule/tls/prepare.yml` runs two plays. The first, on `localhost`, includes `tasks/certificates.yml`. The second installs PostgreSQL and Redis on the target. The fetch and delete tasks are gone.
* `molecule/tls/tasks/certificates.yml` writes to `tls_src_dir` only. It also generates the server certificates for PostgreSQL and Redis, which used to live in the service fixtures.
* `molecule/tls/tasks/postgresql_tls.yml` and `redis_tls.yml` upload their server certificate and the CA certificate with `copy`, instead of generating them with OpenSSL. The client-certificate connection checks are gone, because verify runs the same checks through the files the role uploads.
* `tasks/tls.yml` is replaced by `tasks/tls_upload.yml`, which creates only missing directories, as `0755 root:root`, and no longer deduplicates the upload list. A file listed twice is uploaded twice, and the second copy is a no-op.
* Added `tasks/tls_verify.yml`. Removed `tasks/preflight.yml` and the two permission tasks in `tasks/main.yml`.
* The scenario gives PostgreSQL and Redis separate CAs, client certificates, and directories under `/etc/miarec/tls`, which is how production is configured, so the role creates two directories and verifies six distinct files. `tls_src_dir` is defined once, in `molecule.yml`.
* `molecule/tls/tests/test_tls.py` asserts that the CA private keys aren't on the target, that the server files exist, that the uploaded keys are `root:miarec` 0640 and the certificates 0644 in `0755 root` directories, that the recorder runs as the `miarec` user, and that this user can read the keys through `runuser`.
* Added `.yamllint` and `.gitattributes`. Converted `templates/etc_systemd_system_miarec.service.j2` to LF.
* CI runs the `tls` scenario next to `default` and `sftp`.

---

## Notes for Reviewers

* The template change touches only line endings. On the next deploy, the "Install miarec service | systemd" task reports `changed` once, which notifies the "Start miarec" handler. The handler uses `state: started`, so a running recorder isn't restarted. Later runs are idempotent again.
* The `.yamllint` in ansible-role-miarecweb PR 20 disables the `comments` rule outright. ansible-lint warns about that config and disables fix mode, so this one sets the values ansible-lint asks for instead. Both linters pass.
* The TLS feature has not been deployed to production, so no deployment relied on the removed permission tasks or the preflight checks.
* Unlike ansible-role-miarecweb, this role has no preflight check that requires a non-root user and group for client certificates. The recorder runs as `miarec_bin_user` with primary group `miarec_bin_group`, so it can read a key written as `root:{{ miarec_bin_group }}` 0640 in every combination, and `tls_verify.yml` fails the play if it can't.
* `docs/prs/pr_009_upload_tls_files.md` still describes the fetch-and-delete fixture. It's left as a record of PR 9 as merged.
