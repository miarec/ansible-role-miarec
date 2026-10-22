"""The chrooted SFTP user: a real login with sftp and ssh from inside the container.

converge.yml checks that the role fails on a chroot that sshd refuses.
"""
import os
import shlex

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

SFTP_USER = "miarecsftp"
# converge.yml sets miarec_sftp_group to miarec_bin_group.
RECORDER_USER = os.environ.get("MIAREC_BIN_USER", "miarec")
SFTP_GROUP = os.environ.get("MIAREC_BIN_GROUP", "miarec")
CHROOT = "/var/recordings"
# prepare.yml creates the key, and converge.yml installs its public key for the SFTP user.
SSH_OPTIONS = (
    "-i /root/sftp_test_key -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes "
    "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/sftp_known_hosts"
)


def instance_name(host):
    # miarec_instance_name defaults to the inventory hostname.
    return host.ansible.get_variables()["inventory_hostname"]


def sftp(host, *commands):
    """Run the sftp commands as the SFTP user, and return the result of the batch.

    sftp stops at the first command that fails, and exits with a non-zero code.
    """
    batch = shlex.quote("\n".join(commands) + "\n")
    return host.run(f"printf %s {batch} | sftp {SSH_OPTIONS} -b - {SFTP_USER}@127.0.0.1")


def test_the_chroot_and_its_recordings_dir(host):
    chroot = host.file(CHROOT)
    assert chroot.is_directory
    assert chroot.user == "root"
    assert chroot.group == SFTP_GROUP
    assert chroot.mode == 0o2755

    # install.yml creates the recorder's folder, and sftpuser.yml leaves it as it is.
    recordings = host.file(f"{CHROOT}/{instance_name(host)}")
    assert recordings.is_directory
    assert recordings.user == RECORDER_USER
    assert recordings.group == SFTP_GROUP
    assert recordings.mode == 0o2775


def test_the_sftp_user_logs_in_to_the_chroot(host):
    result = sftp(host, "pwd", "ls -1 /")
    assert result.rc == 0, result.stderr
    assert "Remote working directory: /\n" in result.stdout
    # sftp prints the entries of `ls -1 /` with the leading slash.
    assert f"/{instance_name(host)}" in result.stdout.split()


def test_the_sftp_user_writes_and_reads_in_the_recordings_dir(host):
    name = instance_name(host)
    host.run_test("echo recording > /tmp/sftp-upload.txt")
    try:
        result = sftp(
            host,
            f"put /tmp/sftp-upload.txt /{name}/sftp-upload.txt",
            f"get /{name}/sftp-upload.txt /tmp/sftp-download.txt",
        )
        assert result.rc == 0, result.stderr

        uploaded = host.file(f"{CHROOT}/{name}/sftp-upload.txt")
        assert uploaded.user == SFTP_USER
        # The setgid bit of the recordings dir gives new files its group.
        assert uploaded.group == SFTP_GROUP
        assert host.file("/tmp/sftp-download.txt").content_string == "recording\n"
    finally:
        host.run(f"rm -f /tmp/sftp-upload.txt /tmp/sftp-download.txt {CHROOT}/{name}/sftp-upload.txt")


def test_the_sftp_user_reads_what_the_recorder_user_writes(host):
    name = instance_name(host)
    recording = f"{CHROOT}/{name}/recorder-file.txt"
    host.run_test(f"runuser -u {RECORDER_USER} -- sh -c 'echo recording > {recording}'")
    try:
        result = sftp(host, f"get /{name}/recorder-file.txt /tmp/sftp-download.txt")
        assert result.rc == 0, result.stderr
        assert host.file("/tmp/sftp-download.txt").content_string == "recording\n"
    finally:
        host.run(f"rm -f /tmp/sftp-download.txt {recording}")


def test_the_sftp_user_cannot_write_to_the_chroot(host):
    host.run_test("echo recording > /tmp/sftp-upload.txt")
    try:
        result = sftp(host, "put /tmp/sftp-upload.txt /sftp-upload.txt")
        assert result.rc != 0
        assert "Permission denied" in result.stdout + result.stderr
        assert not host.file(f"{CHROOT}/sftp-upload.txt").exists
    finally:
        host.run(f"rm -f /tmp/sftp-upload.txt {CHROOT}/sftp-upload.txt")


def test_the_sftp_user_has_no_shell(host):
    # ForceCommand internal-sftp: sshd runs SFTP instead of the command.
    result = host.run(f"ssh {SSH_OPTIONS} {SFTP_USER}@127.0.0.1 id")
    assert result.rc != 0
    assert "uid=" not in result.stdout
