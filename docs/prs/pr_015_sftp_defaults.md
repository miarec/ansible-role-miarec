# 2026-11-05-sftp-defaults

Gives the chrooted SFTP user a default layout that sshd accepts, and stops the chroot check from rejecting a symlinked parent that sshd would accept.

## 🎯 Problem

An operator who turns on `miarec_sftp_create_user` with the role's defaults has never had a working SFTP login. The default chroot was the recordings directory itself. sshd requires root to own the chroot and every directory above it, and the recorder needs to write to its own folder, so the two cannot be the same directory. Before PR 10, the play passed and sshd closed every SFTP session. Since PR 10, the play fails on `/var/miarec`, which the role creates as the recorder's user, and the message tells the operator to choose another directory. Either way, the defaults alone don't work.

A second, smaller problem: the chroot check inspects a symlink itself instead of its target. A recordings tree reached through a symlinked parent, such as a separate mount, fails the play with a misleading mode `0777` message, although sshd resolves the link and accepts the chroot.

---

## 👀 What changes for users

The chroot defaults to `/var/recordings`, whose only parent is `/var`, and the recordings directory defaults to `/var/recordings/<miarec_instance_name>` inside it. With `miarec_sftp_create_user: true` and the defaults, the SFTP user logs in, sees the recorder's folder, and reads recordings. Writing needs `miarec_sftp_group` set to `miarec_bin_group`, as before. The README now documents the SFTP variables.

A symlinked parent of the chroot now passes the check when its target is root's and not writable by group or others.

---

## 💥 Impact

* **Who is affected**: every host that relies on the default `miarec_recordings_dir`. The next deploy writes the new `OutputDirectory` to `miarec.ini`, and the recorder writes new recordings to `/var/recordings/<instance>`. Earlier recordings stay in `/var/miarec/recordings` and keep playing from the paths stored in the database. The ansible-miarec playbooks don't pin the directory, so their recorders move too.
* **Who is not affected**: hosts that set `miarec_recordings_dir` themselves, and hosts where the recording directory was changed in the web portal, which takes precedence over the ini.
* **Conditions**: to keep the old location, set `miarec_recordings_dir: /var/miarec/recordings`.

---

## 🔧 Implementation notes

* No task changes for the layout. The recorder's folder is `<miarec_sftp_dir>/<miarec_instance_name>`, so the existing "Create a sub-directory" task skips it, and the chroot check sees only `/var`.
* The `sftp` scenario now runs with the defaults instead of overriding both directories.
* The alternative, creating `/var/miarec` as root in `install.yml` and keeping the old recordings path, was rejected: it adds a task that manages a directory other software may own, and the "Create a sub-directory" task would then create an unused `<miarec_instance_name>` folder next to the recordings.
