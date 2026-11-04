# Molecule test this role

Run Molecule test
```
uv run molecule test
```

Run test with variable example
```
MOLECULE_DISTRO=rockylinux9 MOLECULE_MIAREC_VERSION=7.0.0.100 uv run molecule test
```

## Scenarios
 - `default`: installs MiaRec and checks the service, its ports, and `/health`.
 - `sftp`: installs MiaRec with the chrooted SFTP user (`miarec_sftp_create_user: true`),
   with the chroot `/var/recordings`. The tests log in with `sftp` and a key, read and
   write in the recordings directory, and check that the user can't write to the chroot
   or run a shell. `converge.yml` also checks that the role fails on a chroot that sshd
   refuses: one under a directory that a user other than root owns, as the role creates
   `/var/miarec` for the default `miarec_recordings_dir`, and one under a group-writable
   directory.
   ```
   uv run molecule test -s sftp
   ```
 - `tls`: installs MiaRec with TLS connections to PostgreSQL and Redis, and with SIP
   over TLS on the SIPREC interface on port 5081, with client certificates. The role
   uploads every TLS file from the control machine, where `prepare.yml` puts them.
   The tests check the uploaded files, and send SIP OPTIONS with `openssl s_client`
   with a client certificate of the deployment's CA, without a client certificate,
   and with a client certificate of another CA. `side_effect.yml` renews the
   recorder's certificate on the control machine and runs the role again, which must
   upload it and restart the recorder.
   ```
   uv run molecule test -s tls
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
