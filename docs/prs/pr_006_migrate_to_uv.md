# Pull Request Description Template

## Summary

This PR migrates the Ansible role's dependency management from pip with requirements.txt to uv with pyproject.toml. It also adds multi-architecture support (x86_64 and aarch64) and removes end-of-life distributions.

---

## Purpose

- **Modern dependency management**: uv provides faster, more reliable dependency resolution with lockfile support for reproducible builds
- **Multi-architecture support**: MiaRec can now be installed on ARM64 systems (aarch64) in addition to x86_64
- **Deprecation fixes**: Updates all deprecated `ansible_*` variables to modern `ansible_facts['*']` syntax
- **EOL cleanup**: Removes testing for end-of-life distributions (CentOS 7, Ubuntu 20.04, Rocky Linux 8, RHEL 7, RHEL 8)

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran `ansible-lint`
* Notes: Linting passes with 0 failures. Molecule test configuration updated for uv.

---

## Related Issues

N/A - internal modernization effort

---

## Changes

Brief list of main changes:

* Added `pyproject.toml` and `uv.lock` for uv-based dependency management
* Updated GitHub Actions CI to use `astral-sh/setup-uv@v4` instead of pip
* Replaced deprecated `ansible_*` variables with `ansible_facts['*']` syntax in:
  - `tasks/main.yml`
  - `tasks/install.yml`
  - `tasks/dependencies.yml`
  - `vars/Debian.yml`
  - `vars/RedHat.yml`
* Added dynamic architecture detection using `ansible_facts['architecture']` in tarball filenames
* Removed EOL distros from CI matrix: centos7, ubuntu2004, rockylinux8, rhel7, rhel8
* Added Ubuntu 24.04 (noble) to supported platforms
* Added `ansible.cfg` for proper role path configuration
* Updated molecule configuration with `collections.yml`
* Updated README with uv-based testing instructions
* Updated `.ansible-lint` configuration

---

## Notes for Reviewers

- The CI runner was updated from `ubuntu-20.04` to `ubuntu-22.04` since 20.04 is approaching EOL
- The uv lockfile (`uv.lock`) is auto-generated and should not be manually edited
- Multi-architecture support requires appropriate MiaRec tarballs to be available for both architectures

---

## Docs

* [x] Updated relevant documentation (README.md, molecule/README.md)
