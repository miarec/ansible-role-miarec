# ansible-miarec

Ansible role for installing of MiaRec recorder application.


Role Variables
--------------

- `miarec_version`: The version of miarec files to install
- `miarec_instance_name`: The instance name (default: Recorder). Multiple recorder instances could connect to the same database. Using the unique name for each instance allows to configure each instance individually.
- `miarec_db_host`: The PostgreSQL host (default: 127.0.0.1)
- `miarec_db_port`: The PostgreSQL port (default: 5432)
- `miarec_db_name`: The PostgreSQL database name (default: miarecdb)
- `miarec_db_user`: The ostgreSQL database user (default: miarec)
- `miarec_db_password`: The PostgreSQL database password (default: password)
- `miarec_redis_host`: The Redis host (default: 127.0.0.1)
- `miarec_redis_port`: The Redis port (default: 6379)
- `miarec_install_dir`: The installation directory (default: /opt/miarec)
- `miarec_log_dir`: The location of log files (default: /var/log/miarec)
- `miarec_recordings_dir`: The location for recording files (default: `/var/recordings/{{ miarec_instance_name }}`). This option is configurable via web portal.
- `miarec_sftp_create_user`: Create a chrooted SFTP user for remote access to the recordings (default: false).
- `miarec_sftp_dir`: The chroot of the SFTP user (default: /var/recordings). sshd requires root to own this directory and each of its parents, and none of them can be writable by group or others. The recordings directory lives inside it.
- `miarec_sftp_group`: The group of the SFTP user (default: miarecsftp). Set it to `miarec_bin_group` to let the SFTP user write to the recordings directory.


SIP over TLS on the SIPREC interface
------------------------------------

The recorder can accept SIPREC sessions over TLS, optionally with client certificates (mutual TLS). These variables set the `[Protocol::SIPREC]` section of `miarec.ini`:

| Variable | Default | `miarec.ini` setting | Description |
| --- | --- | --- | --- |
| `miarec_siprec_tls_cert_file` | `""` | `SSLCertificate` | The path of the recorder's certificate on the host. Set it with the key. |
| `miarec_siprec_tls_key_file` | `""` | `SSLPrivateKey` | The path of the recorder's private key on the host. Set it with the certificate. |
| `miarec_siprec_tls_ca_file` | `""` | `SSLCACertificates` | The path of a PEM file on the host with the CA certificates of the clients. Set it to require client certificates. |
| `miarec_siprec_tls_cert_file_src` | `""` | None | A local copy of the certificate. When it's set, the role uploads the file to `miarec_siprec_tls_cert_file` and restarts the recorder when the file changed. Leave it empty when the file is already on the host. |
| `miarec_siprec_tls_key_file_src` | `""` | None | A local copy of the private key, see `miarec_siprec_tls_cert_file_src`. |
| `miarec_siprec_tls_ca_file_src` | `""` | None | A local copy of the CA file, see `miarec_siprec_tls_cert_file_src`. |

The TLS port, `PortTLS`, is a recorder setting of the MiaRec web portal, not a variable of the role: an operator turns TLS on and off there. The role writes the three file settings when any of the paths is set, and restarts the recorder when a setting changes.

### The recorder's certificate and key

The recorder's certificate comes from the CA of your deployment, as the PostgreSQL and Redis client certificates do: the role doesn't create or sign certificates. Put the certificate and the key on the Ansible control machine and set `miarec_siprec_tls_cert_file_src` and `miarec_siprec_tls_key_file_src`, and the role uploads them to the paths of `miarec_siprec_tls_cert_file` and `miarec_siprec_tls_key_file`, as it uploads the PostgreSQL and Redis files: owner `root`, group `miarec_bin_group`, mode `0644` for the certificate and `0640` for the key. A missing directory is created as `0755 root`, and an existing one is left alone. When a file changed, the role restarts the recorder, so a renewed certificate takes effect with the next run. When a `*_src` variable is empty, the file must already be on the host, and the role leaves its permissions as they are.

Before it changes the host, the role verifies that `miarec_bin_user` can read every TLS file in use, uploaded or not, as it does for the PostgreSQL and Redis files, and fails the play when it can't.

Set the certificate and the key together, or neither, or the role fails. When `SSLCertificate` and `SSLPrivateKey` name files that don't exist, the recorder creates a self-signed certificate of its own at startup. A client that verifies or pins the recorder's certificate can't know that certificate before the recorder starts, and the certificate changes whenever its files are lost.

### Client certificates (mutual TLS)

When `miarec_siprec_tls_ca_file` is set, the recorder requires a client certificate signed by one of the CA certificates in that file, and refuses a client without one. When it's empty, the recorder doesn't ask for a client certificate. Set `miarec_siprec_tls_ca_file_src` to upload the file, or put it on the host before you run the role. The file can be the CA file of the PostgreSQL or Redis client. If a client certificate has an extended key usage extension, it must include `clientAuth`.

### Settings in the MiaRec database

The recorder settings that the MiaRec web application stores in the database take precedence over `miarec.ini`, which is the fallback. If the web application sets any of these settings for a recorder, the recorder uses the value from the database, and the role's value has no effect. The TLS port is set there only.


Example Playbook
----------------

eg:

``` yaml
    - name: Install python
      hosts: localhost
      become: yes
      roles:
        - role: ansible-miarec
          miarec_version: 5.2.1.169
```

The above playbook will install miarec version 5.2.1.169.


## Testing

This role uses [Molecule](https://molecule.readthedocs.io/) with Docker for testing.
[uv](https://docs.astral.sh/uv/) is used for dependency management.

### Prerequisites

- Docker
- uv (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Running Tests

```bash
# Run full test suite
uv run molecule test

# Test against specific distro
MOLECULE_DISTRO=ubuntu2404 uv run molecule test
MOLECULE_DISTRO=rockylinux9 uv run molecule test
```

### Available Distros

| Distribution   | Variable Value  |
|----------------|-----------------|
| Ubuntu 22.04   | `ubuntu2204`    |
| Ubuntu 24.04   | `ubuntu2404`    |
| Rocky Linux 9  | `rockylinux9`   |
| RHEL 9         | `rhel9`         |

### Linting

```bash
uv run ansible-lint
```
