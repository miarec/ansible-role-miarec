## Summary

Generate the TLS test certificates on the control machine, so the `tls` Molecule scenario proves that the role creates `/etc/miarec/tls` and uploads the client files. Also add a `.yamllint` config that agrees with `.ansible-lint`, and normalize line endings to LF.

This ports the fixes from ansible-role-miarecweb PR 20 to this role.

---

## Purpose

PR 9 made the role upload the TLS files from the control machine. Its `tls` scenario generated every certificate on the target, inside `/etc/miarec/tls`, the directory the role manages. It then fetched the client files to the control machine and deleted them, so the role could upload them again. This had three flaws:

* The fixture created `/etc/miarec/tls` with its own owner and mode, so the test didn't cover the role creating the directory.
* The CA private key and the OpenSSL scratch files stayed in the role's directory on the target. A failed prepare left the client files there too, and converge then passed without an upload.
* The prepare checks that connected to PostgreSQL and Redis with the client certificate needed the client files on the target, which is the opposite of what the role does in production.

With this change, a play on `localhost` generates the CA, the client certificate, and the PostgreSQL and Redis server certificates in the Molecule ephemeral directory. The PostgreSQL and Redis fixtures upload their own server certificate and the CA certificate. Nothing in prepare writes to `/etc/miarec/tls`. The role creates that directory and uploads the client files during converge, the same way the production playbooks do. The CA private key never reaches the target, and verify asserts that.

### Lint config and line endings

yamllint had no config in this repo, so it ran with the default rules and reported more than a hundred errors, most of them for rules that `.ansible-lint` already skips. `.yamllint` now mirrors those skips and allows spaces inside braces, so `{ src: ca.crt, mode: "0644" }` passes. It also sets the `comments`, `comments-indentation`, and `octal-values` values that ansible-lint requires. Without them, ansible-lint warns that the config is incompatible and turns off its fix mode.

The systemd unit template was committed with CRLF line endings, so every deploy rendered a CRLF unit file. The template is now LF, and `.gitattributes` keeps it that way on a Windows checkout.

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran molecule tests
* Notes:
  - `uv run molecule test -s tls` passes on Ubuntu 24.04. In converge, the role reports `changed` for "Create TLS directories" with `/etc/miarec/tls` and for the upload of the three client files. The 8 testinfra tests pass, including the new check that `/etc/miarec/tls/ca.key` doesn't exist on the target and the check that the server files that prepare uploads exist.
  - `uv run ansible-lint` and `uv run yamllint .` pass without warnings.
  - I didn't run the scenario on the RedHat images locally. CI runs it on every distro.

---

## Related Issues

Fixes the Molecule test flaw in #9. Mirrors miarec/ansible-role-miarecweb#20.

---

## Changes

Brief list of main changes:

* `molecule/tls/prepare.yml` runs two plays. The first, on `localhost`, includes `tasks/certificates.yml`. The second installs PostgreSQL and Redis on the target. The fetch and delete tasks are gone.
* `molecule/tls/tasks/certificates.yml` writes to `tls_src_dir` only. It also generates the server certificates for PostgreSQL and Redis, which used to live in the service fixtures.
* `molecule/tls/tasks/postgresql_tls.yml` and `redis_tls.yml` upload their server certificate and the CA certificate with `copy`, instead of generating them with OpenSSL. The client-certificate connection checks are gone, because verify runs the same checks through the files the role uploads.
* `molecule/tls/tests/test_tls.py` asserts that the CA private key isn't on the target, and that the server files exist.
* Added `.yamllint` and `.gitattributes`. Converted `templates/etc_systemd_system_miarec.service.j2` to LF.

---

## Notes for Reviewers

* The template change touches only line endings. On the next deploy, the "Install miarec service | systemd" task reports `changed` once, which notifies the "Start miarec" handler. The handler uses `state: started`, so a running recorder isn't restarted. Later runs are idempotent again.
* The `.yamllint` in ansible-role-miarecweb PR 20 disables the `comments` rule outright. ansible-lint warns about that config and disables fix mode, so this one sets the values ansible-lint asks for instead. Both linters pass.
* `docs/prs/pr_009_upload_tls_files.md` still describes the fetch-and-delete fixture. It's left as a record of PR 9 as merged.
