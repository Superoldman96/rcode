#!/usr/bin/env python3

import subprocess as sp
import sys
import socket
import time
import uuid
import json

from pathlib import Path

from .ipc import IPCClientSocket, DEFAULT_IPC_PORT

def init_key_file():
    key_file = Path.home() / "rssh.keyfile"

    my_key = str(uuid.uuid4())
    if not key_file.exists():
        key_file.write_text(my_key) 


def find_destination_position(args):
    for i, arg in enumerate(args):
        if not arg.startswith('-'):
            return i
    return -1

def create_ssh_args(addr: str, session: dict, args: list):
    dest_pos = find_destination_position(args)
    if dest_pos == -1:
        proc = sp.run(['ssh'] + args)
        sys.exit(proc.returncode)

    hostname = args[dest_pos]
    print(hostname)
    pre_dest = args[:dest_pos]
    post_dest = args[dest_pos:]
    if '-t' not in pre_dest:
        pre_dest.append('-t')
    
    sid = session["sid"]
    key = session["key"]
    ipc_sock = f"/tmp/rssh-ipc-{sid}.sock"
    pre_dest.extend(["-R", f"{ipc_sock}:{addr}"])

    remote_command = f'export RSSH_SID={sid}; export RSSH_SKEY={key}; exec $SHELL'
    post_dest.append(remote_command)

    return pre_dest + post_dest
    

def start_ipc_server():
    if sys.platform == "win32":
        proc = sp.Popen(
            ["rssh-ipc"],
            stdout=sp.DEVNULL,
            creationflags=sp.CREATE_NO_WINDOW,
            stderr=sp.STDOUT
        )
    else:
        proc = sp.Popen(
            ["rssh-ipc"],
            stdout=sp.DEVNULL,
            stderr=sp.STDOUT,
            start_new_session=True
        )

    return proc
    
    
def connect_to_rpc_server(host: str, port: int):
    socks_client = IPCClientSocket()
    try:
        socks_client.connect((host, port))
        print("connect to rpc server success")
    except socket.error:
        print("start ipc server")
        start_ipc_server()
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

def create_session(sock: IPCClientSocket):
    keyfile = Path.home() / "rssh.keyfile"

    session_payload = {
        "method": "new_session",
        "params": {
            "hostname": "debian",
            "keyfile": keyfile.read_text()
        }
    }

    sock.write(session_payload)
    res = json.loads(sock.read())
    if res.get("code") != 0:
        print("Error: Failed to create session, ", res.get("message"), file=sys.stderr)
        sys.exit(1)

    return res.get("data")

def parse_ipc_args(args):
    host = "127.0.0.1"
    if len(args) > 0 and "-ia" == args[0]:
        host = args[1]
        args = args[2:]

    port = DEFAULT_IPC_PORT
    if len(args) > 0 and "-il" == args[0]:
        port = args[1]
        args = args[2:]
    
    return host, port, args

def main():
    init_key_file()

    args = sys.argv[1:]  # remove rssh itself
    if "-R" in args:
        print("Error: -R is not allowed.", file=sys.stderr)
        sys.exit(1)

    host, port, args = parse_ipc_args(args)

    with connect_to_rpc_server(host, port) as sock:
        session = create_session(sock)
        addr = f"{host}:{port}"
        ssh_args = create_ssh_args(addr, session, args)
        
        try:
            proc = sp.run(['ssh'] + ssh_args)
            sys.exit(proc.returncode)
        except KeyboardInterrupt:
            pass

    

if __name__ == '__main__':
    main() 