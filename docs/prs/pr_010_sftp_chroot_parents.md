## Summary

Fail the play when sshd would refuse the chroot of the SFTP user, instead of reporting success with a broken SFTP login.

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

---

## Testing

How did you verify it works?

* [ ] Added/updated tests
* [x] Ran molecule tests
* Notes: The Molecule scenarios don't turn on the SFTP user, so I tested by hand in the `default` scenario's container (Ubuntu 24.04), with `openssh-server` installed in the container:
  - `molecule converge` with the defaults: passed. `/var/miarec` is `miarec:miarec 2775`.
  - `molecule converge -- -e miarec_sftp_create_user=true`: failed at the new check with the message above.
  - `molecule converge -- -e miarec_sftp_create_user=true -e miarec_sftp_dir=/var/recordings -e miarec_recordings_dir=/var/recordings/ansible-role-miarec -e miarec_sftp_pubkey_file=<test key>`: passed. An SFTP login as `miarecsftp` with the test key listed the recorder's folder.
  - `ansible-lint` passes.

---

## Related Issues

N/A

---

## Changes

Brief list of main changes:

* Added two tasks to `tasks/sftpuser.yml`, after the SFTP share directory is created: `stat` each parent directory of `miarec_sftp_dir`, then `assert` that root owns it and that neither group nor others can write to it.

---

## Notes for Reviewers

* This affects only hosts with `miarec_sftp_create_user: true`.
* A host with `miarec_sftp_create_user: true` and the default `miarec_recordings_dir` now fails at the new check. Before this change, the play passed but SFTP didn't work on such a host, so no working setup breaks. To fix such a host, set `miarec_sftp_dir` to a directory whose parents root owns, such as `/var/recordings`, with `miarec_recordings_dir` inside it, or change the owner and mode of `/var/miarec`.
* A follow-up could turn on the SFTP user in a Molecule scenario and test a login, so that CI covers this path.
