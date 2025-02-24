#!/usr/bin/env python3

import subprocess as sp
import argparse
import sys
import socket
import time
import uuid
import json
import os

from pathlib import Path

from .ipc import IPCClientSocket, DEFAULT_IPC_PORT

KEY_FILE = Path.home() / ".rssh/keyfile"
CONFIG_FILE = Path.home() / '.rssh/config'


def init_files():
    if not KEY_FILE.parent.exists():
        KEY_FILE.parent.mkdir(parents=True)

    my_key = str(uuid.uuid4())
    if not KEY_FILE.exists():
        KEY_FILE.write_text(my_key)

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text("")


def find_destination_position(args):
    for i, arg in enumerate(args):
        if not arg.startswith("-"):
            return i
    return -1


def create_ssh_args(ipc_host: str, ipc_port: int, args: list):
    try:
        sock = connect_to_rpc_server(ipc_host, ipc_port)
        dest_pos = find_destination_position(args)
        if dest_pos == -1:
            proc = sp.run(["ssh"] + args)
            sys.exit(proc.returncode)

        hostname = args[dest_pos]
        pre_dest = args[:dest_pos]
        post_dest = args[dest_pos:]
        if "-t" not in pre_dest:
            pre_dest.append("-t")

        session = create_session(sock, hostname)
        sock.close()

        sid = session["sid"]
        key = session["key"]
        addr = f"{ipc_host}:{ipc_port}"
        ipc_sock = f"/tmp/rssh-ipc-{sid}.sock"
        pre_dest.extend(["-R", f"{ipc_sock}:{addr}"])

        remote_command = f"export RSSH_SID={sid}; export RSSH_SKEY={key}; exec $SHELL"
        post_dest.append(remote_command)

        return pre_dest + post_dest
    finally:
        sock.close()


def start_ipc_server(host: str, port: int):
    if sys.platform == "win32":
        proc = sp.Popen(
            ["rssh-ipc", "--host", host, "--port", str(port)],
            stdout=sp.DEVNULL,
            creationflags=sp.CREATE_NO_WINDOW,
            stderr=sp.STDOUT,
        )

    else:
        proc = sp.Popen(
            ["rssh-ipc", "--host", host, "--port", str(port)],
            stdout=sp.DEVNULL,
            stderr=sp.STDOUT,
            start_new_session=True
        )

    return proc


def connect_to_rpc_server(host: str, port: int):
    socks_client = IPCClientSocket()
    try:
        socks_client.connect((host, port))
        print("Connected to RPC server successfully")
    except socket.error:
        print("Starting IPC server...")
        start_ipc_server(host, port)
        time.sleep(0.2)

    if socks_client.connected:
        return socks_client

    for _ in range(10):
        try:
            socks_client = IPCClientSocket()
            socks_client.connect((host, port))
            if socks_client.connected:
                break
        except socket.error:
            time.sleep(0.1)

    if not socks_client.connected:
        print("Error: Failed to connect to RPC server", file=sys.stderr)
        sys.exit(1)

    return socks_client


def create_session(sock: IPCClientSocket, hostname: str):
    session_payload = {
        "method": "new_session",
        "params": {
            "pid": os.getpid(),
            "hostname": hostname,
            "keyfile": KEY_FILE.read_text()
        },
    }

    sock.write(session_payload)
    res = json.loads(sock.read())
    if res.get("code") != 0:
        print("Error: Failed to create session, ", res.get("message"), file=sys.stderr)
        sys.exit(1)

    return res.get("data")


def parse_ipc_args(args):
    parser = argparse.ArgumentParser(description="IPC Server")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        required=False,
        help="host to listen on (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_IPC_PORT,
        required=False,
        help=f"Port to listen on (default: {DEFAULT_IPC_PORT})",
    )

    argv, args = parser.parse_known_args(args)

    return argv.host, argv.port, args


def run_ssh(ssh_args):
    if sys.platform == "win32":
        proc = sp.run(
            ['ssh'] + ssh_args,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        sys.exit(proc.returncode)
    else:
        os.execvp("ssh", ["ssh"] + ssh_args)


def launch(args):
    init_files()

    if "-R" in args or "-T" in args:
        print("Error: -R and -T isn't allowed when using rssh.", file=sys.stderr)
        sys.exit(1)

    ipc_host, ipc_port, ssh_args = parse_ipc_args(args)
    try:
        ssh_args = create_ssh_args(ipc_host, ipc_port, ssh_args)
        run_ssh(ssh_args)
    except ConnectionError:
        print("Error: Failed to connect to RPC server", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


def main():
    launch(sys.argv[1:])


def ssh_wrapper():
    args = sys.argv[1:]

    if "--rssh" in args:
        args.remove("--rssh")
        print("rssh is enabled")
        launch(args)
    else:
        run_ssh(args)


if __name__ == "__main__":
    main()
