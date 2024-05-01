# Molecule test this role

Run Molecule test
```
molecule test
```

Run test with variable example
```
MOLECULE_DISTRO=centos7 MOLECULE_MIAREC_VERSION=7.0.0.100 molecule test
```

## Variables
 - `MOLECULE_DISTRO` OS of docker container to test, default `ubuntu2204`
    List of tested distros
    - `ubuntu2204`
    - `ubuntu2004`
    - `centos7`
    - `rockylinux9`
    - `rockylinux8`
    - `rhel9`
    - `rhel8`
    - `rhel7`
 - `MOLECULE_MIAREC_VERSION` defines variable `miarec_version`, default `2024.4.5.0`
 - `MOLECULE_ANSIBLE_VERBOSITY` set verbosity for ansible run, like running "ansible -vvv", values 0-3, default 0
