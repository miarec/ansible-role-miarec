# 2026-11-05-tls-ini-on-redeploy

Fixes a medium-severity bug where turning TLS off, or clearing the SIPREC certificate paths, has no effect on a recorder that already runs the deployed version.

## 🎯 Problem

An operator who disables PostgreSQL or Redis TLS in the inventory, or removes the SIPREC certificate paths, and reruns the playbook expects the recorder to follow. On a host that already has that recorder version, it doesn't. The recorder keeps connecting to the database and Redis over TLS and fails once the server stops offering it, or keeps serving the old SIPREC certificate and keeps requiring client certificates. The play reports success.

---

## 👀 What changes for users

Before, a TLS setting could only be turned on by a deploy. Turning it off needed a new recorder version or a manual edit of `miarec.ini`. After, every deploy writes the current value of `UseSSL` for the PostgreSQL and Redis connections, and the current SIPREC certificate, key and CA paths, so disabling or clearing them takes effect on the next deploy. Turning TLS on works as before.

---

## 🐛 Bug details

* **Severity**: medium. A workaround exists: edit `miarec.ini` by hand, or bump the recorder version.
* **Symptom**: after a deploy that disables TLS, the recorder still connects over TLS and fails when the server no longer accepts it. After a deploy that clears the SIPREC paths, the SIPREC listener still presents the old certificate and still rejects clients without a certificate.
* **Exposure**: the PostgreSQL and Redis part since TLS support arrived in bd619ee on 2025-12-10 (PR 8). The SIPREC part since PR 12, merged today. The release directory is keyed by version and `miarec.ini` is extracted once, so the gated tasks never revisit an existing file. ansible-role-miarec-screen fixed the same bug in its d28ecf6.

---

## 💥 Impact

* **Who is affected**: hosts redeployed with the same `miarec_version` after a TLS variable changed from on to off, or after a SIPREC path was cleared.
* **Who is not affected**: first installs, upgrades to a new version, and deploys that turn TLS on. These produced the right file before and still do.
* **Conditions**: same recorder version on the host, and a TLS variable that was on in an earlier deploy.

---

## 🔧 Implementation notes

* `UseSSL` moves into the task that always configures the ini and takes its value from the variable. The certificate paths and `CheckHostName` stay gated on the flag, because the recorder ignores them when `UseSSL` is false.
* The SIPREC task loses its condition. An empty value is the stock ini content, which the default scenario already asserts, and an empty `SSLCACertificates` turns client certificates off. The upload and verify tasks keep their condition.
