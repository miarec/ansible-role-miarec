# 2026-10-04-upload-tls-files

Moves the TLS file upload into the role, so a renewed certificate restarts only the service that reads it.

## 🎯 Problem

The ansible-miarec playbooks deploy several services, often on one host, and upload the TLS files of each service with a shared task in `pre_tasks`. Each play then restarts its service from `post_tasks` when a variable registered by that task reports a change. Registered variables survive across plays, so one changed certificate restarts every service deployed later on the same host, including services that never read the file. The playbooks also depend on a variable name internal to the shared task file.

---

## 👀 What changes for users

Before, the role expected the TLS files to exist on the host and failed early when one was missing. After, setting `miarec_db_tls_*_src` and `miarec_redis_tls_*_src` makes the role copy the files from the Ansible control machine, set root ownership with mode 0644 for certificates and 0640 for private keys readable by `miarec_bin_group`, and restarts the recorder when a file changed. Leaving the variables empty, the default, keeps the previous behavior.

---

## 💥 Impact

* **Who is affected**: deployments that set the new `*_src` variables, starting with ansible-miarec.
* **Who is not affected**: existing deployments. The defaults are empty, so no new task runs and no restart is added.
* **Conditions**: `miarec_db_use_ssl` or `miarec_redis_use_ssl` enabled and at least one `*_src` variable set.

---

## 🔧 Implementation notes

* The upload runs after the user and group are created and before the existing permission tasks, which still cover files that arrive by other means.
* The PostgreSQL and Redis clients usually share one CA file. The file list is deduplicated by destination, so a shared file is uploaded once.
* The preflight check skips a file that has a `*_src` variable, because the copy task reports a missing source. Files without one are still checked on the host.
* The TLS Molecule scenarios move the generated files to the control machine and let the role upload them, so a passing test proves the upload. The fixtures no longer create the service group ahead of time. The scenarios load the role by path, like ansible-role-miarecweb does, so they also work when the repository is checked out under another directory name.
