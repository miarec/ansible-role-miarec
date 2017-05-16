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




