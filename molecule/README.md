# Molecule test this role

Run Molecule test
```
uv run molecule test
```

Run test with variable example
```
MOLECULE_DISTRO=rockylinux9 MOLECULE_MIAREC_VERSION=7.0.0.100 uv run molecule test
```

## Variables
 - `MOLECULE_DISTRO` OS of docker container to test, default `ubuntu2404`
    List of tested distros
    - `ubuntu2204`
    - `ubuntu2404`
    - `rockylinux9`
    - `rhel9`
 - `MOLECULE_MIAREC_VERSION` defines variable `miarec_version`, default `2024.6.2.0`
 - `MOLECULE_ANSIBLE_VERBOSITY` set verbosity for ansible run, like running "ansible -vvv", values 0-3, default 0
