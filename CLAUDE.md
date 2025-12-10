This file provides guidance to coding agent when working with code in this repository.

## Overview

This is an Ansible role (`ansible-role-miarec`) for installing the MiaRec call recording application on Linux servers. It supports both Debian-based (Ubuntu) and RedHat-based (CentOS, RHEL, Rocky Linux) distributions.

## Common Commands

### Setup Development Environment
```bash
# Install dependencies using uv (creates .venv automatically)
uv sync

# Install required Ansible collections
ansible-galaxy collection install community.docker ansible.posix
```

### Linting
```bash
uv run ansible-lint
```

### Testing with Molecule
```bash
# Run full test suite (default: ubuntu2404)
uv run molecule test

# Test specific distro and version
MOLECULE_DISTRO=centos7 MOLECULE_MIAREC_VERSION=7.0.0.100 uv run molecule test

# Individual molecule stages
uv run molecule create    # Create test container
uv run molecule converge  # Run the playbook
uv run molecule verify    # Run testinfra tests
uv run molecule destroy   # Cleanup
```

### Environment Variables for Testing
- `MOLECULE_DISTRO` - Docker image to test (ubuntu2004, ubuntu2204, ubuntu2404, centos7, rockylinux8, rockylinux9, rhel7, rhel8, rhel9)
- `MOLECULE_MIAREC_VERSION` - MiaRec version to install
- `MOLECULE_ANSIBLE_VERBOSITY` - Ansible verbosity 0-3

## Architecture

### Role Structure
- `tasks/main.yml` - Entry point; orchestrates install flow: load OS vars → install deps → create user/group → deploy_helper init → install → cleanup → SFTP user
- `tasks/install.yml` - Core installation: downloads tarball, extracts, configures miarec.ini, sets up systemd/upstart service
- `tasks/dependencies.yml` - OS-specific package dependencies
- `tasks/sftpuser.yml` - Optional restricted SFTP user creation
- `defaults/main.yml` - All configurable variables with defaults
- `vars/Debian.yml`, `vars/RedHat.yml` - OS-family specific variables (tarball filenames)

### Deployment Strategy
Uses Ansible's `deploy_helper` module for versioned deployments:
```
/opt/miarec/
├── releases/
│   ├── 1.0.0.100/
│   ├── 2.0.1.200/
│   └── 3.1.2.5/
├── shared/           # Working directory, persists across releases
└── current -> releases/3.1.2.5   # Symlink to active version
```

### Testing
- Uses Molecule with Docker driver
- Testinfra for verification (`molecule/default/tests/test_defaults.py`)
- Tests verify: directories exist, files deployed, service running/enabled, ports listening (9080, 5080, 6554, 6088)
- CI runs against matrix of all supported distros via GitHub Actions

### Key Configuration
The role configures `miarec.ini` with database (PostgreSQL), Redis, logging, and API settings. Custom INI settings can be passed via `miarec_custom_ini_settings` list.
