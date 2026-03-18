## Summary

Add TLS/SSL support for PostgreSQL and Redis connections in MiaRec, enabling secure encrypted communication with databases.

---

## Purpose

Enterprise deployments often require encrypted database connections to meet security compliance requirements. This PR adds configurable TLS support for both PostgreSQL and Redis, including mutual TLS (mTLS) with client certificate authentication.

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran molecule tests
* Notes: Added new `molecule/tls` scenario that:
  - Generates CA, server, and client certificates
  - Configures PostgreSQL with SSL and client certificate verification
  - Configures Redis with TLS and client certificate authentication
  - Verifies MiaRec connects successfully via TLS to both services
  - Tests the `/health` endpoint to confirm database and Redis connectivity

---

## Related Issues

N/A

---

## Changes

Brief list of main changes:

* Added new role variables for PostgreSQL TLS configuration (`miarec_db_use_ssl`, `miarec_db_tls_ca_file`, `miarec_db_tls_cert_file`, `miarec_db_tls_key_file`, `miarec_db_tls_check_hostname`)
* Added new role variables for Redis TLS configuration (`miarec_redis_use_ssl`, `miarec_redis_tls_ca_file`, `miarec_redis_tls_cert_file`, `miarec_redis_tls_key_file`, `miarec_redis_tls_check_hostname`)
* Added conditional TLS configuration in `tasks/install.yml` for SQLConfig, SQLCallsLog, and RedisCallsLog sections
* Added preflight checks (`tasks/preflight.yml`) to validate TLS certificate files exist and are readable
* Created comprehensive `molecule/tls` test scenario with certificate generation and database TLS setup
* Fixed INJECT_FACTS_AS_VARS deprecation warnings by using `ansible_facts['key']` syntax throughout

---

## Notes for Reviewers

* TLS is disabled by default (`miarec_db_use_ssl: false`, `miarec_redis_use_ssl: false`) - no breaking changes for existing deployments
* Client certificates are optional but recommended for mTLS; the role supports both server-only TLS and full mTLS
* The preflight checks ensure certificate files exist before attempting to configure TLS
* The `molecule/tls` scenario provides a complete integration test including PostgreSQL `hostssl` with `clientcert=verify-ca` and Redis with `tls-auth-clients yes`

---

## Docs

* [x] Updated relevant documentation (new variables documented in defaults/main.yml)
