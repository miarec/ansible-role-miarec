## Summary

Add PostgreSQL and Redis to the molecule test environment to enable realistic integration testing of MiaRec's database and cache connectivity.

---

## Purpose

Previously, molecule tests only verified that MiaRec services started and ports were listening. This change adds actual PostgreSQL and Redis services to the test environment, allowing verification that MiaRec can successfully connect to its dependencies. This catches configuration issues that would otherwise only appear in production deployments.

---

## Testing

* [x] Added/updated tests
* [ ] Ran molecule tests
* Notes: Added `test_health_endpoint()` that verifies MiaRec's `/health` endpoint returns `ok` status for both database and Redis connections.

---

## Related Issues

N/A

---

## Changes

* Added `prepare.yml` playbook to set up test dependencies before converge
* Added `tasks/postgresql.yml` - installs and configures PostgreSQL with miarec user/database
* Added `tasks/redis.yml` - installs and starts Redis service
* Added health endpoint test in `test_defaults.py` that verifies database and Redis connectivity
* Handles OS-specific differences:
  - Debian: uses `pg_lsclusters` for cluster path discovery, `redis-server` service name
  - RedHat: uses `postgresql-setup --initdb`, `redis` service name
  - Note: RedHat 9 has `curl-minimal` which conflicts with `curl`, so curl is only installed on Debian

---

## Notes for Reviewers

* The PostgreSQL setup is modeled after `ansible-role-miarecweb/molecule/default/tasks/postgresql.yml` for consistency
* The `pg_hba.conf` is configured to allow md5 authentication from localhost for the miarec user
* The test credentials (`miarec`/`password`) match what MiaRec expects by default

---

## Docs

* [ ] Updated relevant documentation
