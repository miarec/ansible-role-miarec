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
- `miarec_recordings_dir`: The location for recording files (default: /var/miarec/recordings). This option is configurable via web portal.


SIP over TLS on the SIPREC interface
------------------------------------

The recorder can accept SIPREC sessions over TLS, optionally with client certificates (mutual TLS). These variables set the `[Protocol::SIPREC]` section of `miarec.ini`:

| Variable | Default | `miarec.ini` setting | Description |
| --- | --- | --- | --- |
| `miarec_siprec_tls_port` | `0` | `PortTLS` | The TLS port, for example, `5081`. `0` turns TLS off. |
| `miarec_siprec_tls_cert_file` | `""` | `SSLCertificate` | The path of the recorder's certificate on the host. Required when TLS is on. |
| `miarec_siprec_tls_key_file` | `""` | `SSLPrivateKey` | The path of the recorder's private key on the host. Required when TLS is on. |
| `miarec_siprec_tls_ca_file` | `""` | `SSLCACertificates` | The path of a PEM file on the host with the CA certificates of the clients. Set it to require client certificates. |
| `miarec_siprec_tls_cert_file_src` | `""` | None | A local copy of the certificate. When it's set, the role uploads the file to `miarec_siprec_tls_cert_file` and restarts the recorder when the file changed. Leave it empty when the file is already on the host. |
| `miarec_siprec_tls_key_file_src` | `""` | None | A local copy of the private key, see `miarec_siprec_tls_cert_file_src`. |
| `miarec_siprec_tls_ca_file_src` | `""` | None | A local copy of the CA file, see `miarec_siprec_tls_cert_file_src`. |

The role always sets `PortTLS`, so that setting `miarec_siprec_tls_port` to `0` turns TLS off on a host where it was on. It sets the other three settings only when TLS is on. When a setting changes, the role restarts the recorder.

### The recorder's certificate and key

The recorder's certificate comes from the CA of your deployment, as the PostgreSQL and Redis client certificates do: the role doesn't create or sign certificates. Put the certificate and the key on the Ansible control machine and set `miarec_siprec_tls_cert_file_src` and `miarec_siprec_tls_key_file_src`, and the role uploads them to the paths of `miarec_siprec_tls_cert_file` and `miarec_siprec_tls_key_file`, as it uploads the PostgreSQL and Redis files: owner `root`, group `miarec_bin_group`, mode `0644` for the certificate and `0640` for the key. A missing directory is created as `0755 root`, and an existing one is left alone. When a file changed, the role restarts the recorder, so a renewed certificate takes effect with the next run. When a `*_src` variable is empty, the file must already be on the host, and the role leaves its permissions as they are.

Before it changes the host, the role verifies that `miarec_bin_user` can read every TLS file in use, uploaded or not, as it does for the PostgreSQL and Redis files, and fails the play when it can't.

The role requires both paths when TLS is on because, when `SSLCertificate` and `SSLPrivateKey` name files that don't exist, the recorder creates a self-signed certificate of its own at startup. A client that verifies or pins the recorder's certificate can't know that certificate before the recorder starts, and the certificate changes whenever its files are lost.

### Client certificates (mutual TLS)

When `miarec_siprec_tls_ca_file` is set, the recorder requires a client certificate signed by one of the CA certificates in that file, and refuses a client without one. When it's empty, the recorder doesn't ask for a client certificate. Set `miarec_siprec_tls_ca_file_src` to upload the file, or put it on the host before you run the role. The file can be the CA file of the PostgreSQL or Redis client. If a client certificate has an extended key usage extension, it must include `clientAuth`.

### Settings in the MiaRec database

The recorder settings that the MiaRec web application stores in the database take precedence over `miarec.ini`, which is the fallback. If the web application sets any of these settings for a recorder, the recorder uses the value from the database, and the role's value has no effect.


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
