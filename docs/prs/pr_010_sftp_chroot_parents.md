## Summary

Fail the play when sshd would refuse the chroot of the SFTP user, instead of reporting success with a broken SFTP login. Also stop two tasks from changing the owner of the recorder's folder back and forth on every run, and add a Molecule scenario, `sftp`, that tests a real SFTP login in CI.

---

## Purpose

sshd checks every directory on the path to `ChrootDirectory`, not only the chroot itself. Root must own each one, and no group or other user may write to it. Otherwise sshd accepts the SFTP user's key and then closes the session with `fatal: bad ownership or modes for chroot directory component`.

The role gives the SFTP share directory (`miarec_sftp_dir`) to root, but it doesn't check the directory's parents. With the default `miarec_recordings_dir`, `/var/miarec/recordings`, the "Create recordings directory" task in `tasks/install.yml` creates the missing parent `/var/miarec` with owner `miarec_bin_user` and mode 2775. sshd then refuses every SFTP session, but the play reports success.

The SIPREC SBC end-to-end test in AWS found this: the recorders installed without errors, and SFTP to the recordings failed with the error above for `/var/miarec/`.

With this change, `tasks/sftpuser.yml` runs `stat` on each parent of `miarec_sftp_dir` and fails with a message that names the directory, its owner, and its mode. For example:

```
sshd refuses '/var/miarec/recordings' as the chroot of the SFTP user 'miarecsftp': its parent directory
'/var/miarec' has owner 'miarec' and mode 2775. Each parent directory of miarec_sftp_dir must be owned by
root and must not be writable by group or others. Change the owner and mode of '/var/miarec', or set
miarec_sftp_dir to a directory whose parents meet these requirements, for example, a directory directly
under /var.
```

The role doesn't change the owner or mode of the parent directories, because other software can use them.

### The owner of the recorder's folder

A working layout puts the recorder's folder in the chroot, as `<miarec_sftp_dir>/<miarec_instance_name>`. For example, the SIPREC SBC test uses `miarec_sftp_dir: /var/recordings` and `miarec_recordings_dir: /var/recordings/{{ miarec_instance_name }}`. In this layout, two tasks manage the same directory:

* "Create recordings directory" in `tasks/install.yml` sets `miarec_bin_user:miarec_bin_group`, mode 2775.
* "Create a sub-directory inside sftpuser's home dir" in `tasks/sftpuser.yml` sets `miarec_sftp_user:miarec_sftp_group`, mode 2775.

So every run reports a change, and the owner changes twice. The new Molecule scenario's idempotence step found this. With this change, the `sftpuser.yml` task skips the directory when it is `miarec_recordings_dir`, and the directory keeps the owner from `install.yml`. sshd checks only the chroot and its parents, not the directories inside the chroot, so `miarec_bin_user` can own the recorder's folder.

---

## Testing

How did you verify it works?

* [x] Added/updated tests
* [x] Ran molecule tests
* Notes: The new scenario, `molecule/sftp`, installs `openssh-server` and MiaRec with the SFTP user, the chroot `/var/recordings`, and the recorder's folder `/var/recordings/<instance>`.
  - testinfra tests, which run `sftp` and `ssh` inside the container with a test key:
    - The chroot is `root:<miarec_sftp_group>` 2755, and the recorder's folder is `miarec_bin_user`'s.
    - The SFTP user logs in to `/` and sees the recorder's folder.
    - The SFTP user writes a file to the recorder's folder and reads it back.
    - The SFTP user reads a file that `miarec_bin_user` wrote.
    - The SFTP user can't write to the chroot itself or run a shell command.
  - `converge.yml` also runs `tasks/sftpuser.yml` with two chroots that sshd refuses, and checks that the role fails on the right parent: one whose parent is owned by a user other than root, and one whose parent is group-writable.
  - `uv run molecule test -s sftp` passes on Ubuntu 24.04, including idempotence. Without the `sftpuser.yml` change, idempotence fails on the two tasks above.
  - CI now runs the `default` and `sftp` scenarios on every distro. I didn't run `sftp` on `ubuntu2204`, `rockylinux9`, or `rhel9` locally.
  - `ansible-lint` passes.

---

## Related Issues

N/A

---

## Changes

Brief list of main changes:

* Added two tasks to `tasks/sftpuser.yml`, after the SFTP share directory is created: `stat` each parent directory of `miarec_sftp_dir`, then `assert` that root owns it and that neither group nor others can write to it.
* "Create a sub-directory inside sftpuser's home dir" in `tasks/sftpuser.yml` skips the directory when it is `miarec_recordings_dir`.
* Added the Molecule scenario `molecule/sftp`, and described the scenarios in `molecule/README.md`.
* CI runs `molecule test -s <scenario>` for `default` and `sftp`.

---

## Notes for Reviewers

* This affects only hosts with `miarec_sftp_create_user: true`.
* A host with `miarec_sftp_create_user: true` and the default `miarec_recordings_dir` now fails at the new check. Before this change, the play passed but SFTP didn't work on such a host, so no working setup breaks. To fix such a host, set `miarec_sftp_dir` to a directory whose parents root owns, such as `/var/recordings`, with `miarec_recordings_dir` inside it, or change the owner and mode of `/var/miarec`.
* When the recorder's folder is `<miarec_sftp_dir>/<miarec_instance_name>`, its owner is now `miarec_bin_user:miarec_bin_group` after every run. Before, the run ended with `miarec_sftp_user:miarec_sftp_group`. The SFTP user can still read the folder. To write to it, the SFTP user needs `miarec_sftp_group` set to `miarec_bin_group`, as the `sftp` scenario and the SIPREC SBC test do.
* Not fixed here: when `miarec_sftp_dir` is `miarec_recordings_dir`, which is the default, the chroot is the recorder's folder. `install.yml` makes it `miarec_bin_user` 2775, and `sftpuser.yml` makes it root 2755, so the owner still changes on every run, and the recorder can't write to a root-owned chroot. With the default paths, the new check fails first, on `/var/miarec`.
* CI time about doubles, because each distro also runs the `sftp` scenario.
