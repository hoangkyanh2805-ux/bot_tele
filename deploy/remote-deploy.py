#!/usr/bin/env python3
"""Deploy bot len VPS qua SSH (can password)."""
from __future__ import annotations

import argparse
import getpass
import pathlib
import sys

import paramiko


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy Telegram bot len VPS")
    parser.add_argument("--host", default="103.97.126.28")
    parser.add_argument("--port", type=int, default=2018)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument(
        "--script",
        default=str(pathlib.Path(__file__).with_name("vps-paste.sh")),
    )
    args = parser.parse_args()

    password = args.password or getpass.getpass(f"Password {args.user}@{args.host}: ")
    script_path = pathlib.Path(args.script)
    if not script_path.is_file():
        print(f"Khong tim thay script: {script_path}", file=sys.stderr)
        return 1

    script = script_path.read_text(encoding="utf-8")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"Ket noi {args.user}@{args.host}:{args.port} ...")
    client.connect(
        args.host,
        port=args.port,
        username=args.user,
        password=password,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )
    print("Upload script...")
    sftp = client.open_sftp()
    with sftp.file("/tmp/vps-paste.sh", "w") as remote:
        remote.write(script)
    sftp.chmod("/tmp/vps-paste.sh", 0o755)
    sftp.close()

    print("Cai dat (1-2 phut)...")
    _, stdout, stderr = client.exec_command("bash /tmp/vps-paste.sh", get_pty=True, timeout=300)
    output = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    print(output)
    if err.strip():
        print(err, file=sys.stderr)
    client.exec_command("rm -f /tmp/vps-paste.sh")
    client.close()
    print(f"Exit code: {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
