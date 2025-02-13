#!/usr/bin/env python3

import subprocess as sp
import sys
import socket
import time
import uuid
import json

from pathlib import Path

from ipc import IPCServerSocket, DEFAULT_IPC_PORT, DELIMITER

ROOT_DIR = Path.home() / ".rcode"

def init_root_dir():
    migration = ROOT_DIR.is_file()
    if migration:
        ROOT_DIR.rename(ROOT_DIR.with_name('rcode.bk'))

    if not ROOT_DIR.exists():
        ROOT_DIR.mkdir(parents=True)
    
    config_file = ROOT_DIR / "rssh.config"
    key_file = ROOT_DIR / "rssh.keyfile"

    if not config_file.exists():
        config_file.write_text("")

    my_key = str(uuid.uuid4())
    if not key_file.exists():
        key_file.write_text(my_key) 

    if migration:
        file = Path.home() / "rcode.bk"
        file.rename(ROOT_DIR / "rcode")

def find_destination_position(args):
    for i, arg in enumerate(args):
        if not arg.startswith('-'):
            return i
    return -1

def establish_ssh_connection(session):
    args = sys.argv[1:]  # remove rssh itself
    if "-R" in args:
        print("Error: -R is not allowed.", file=sys.stderr)
        sys.exit(1)

    host = "127.0.0.1"
    if len(args) > 0 and "-ia" == args[0]:
        host = args[1]
        args = args[2:]

    port = DEFAULT_IPC_PORT
    if len(args) > 0 and "-il" == args[0]:
        port = args[1]
        args = args[2:]

    dest_pos = find_destination_position(args)
    if dest_pos == -1:
        proc = sp.run(['ssh'] + args)
        sys.exit(proc.returncode)

    pre_dest = ["ssh"] + args[:dest_pos]
    post_dest = args[dest_pos:]
    if '-t' not in pre_dest:
        pre_dest.append('-t')
    
    sid = session["sid"]
    key = session["key"]
    ipc_sock = f"/tmp/rssh-ipc-{sid}.sock"
    pre_dest.extend(["-R", f"{ipc_sock}:{host}:{port}"])

    remote_command = f'export RSSH_SID={sid}; export RSSH_SKEY={key}; exec $SHELL'
    post_dest.append(remote_command)
    
    ssh_args = pre_dest + post_dest

    try:
        print(ssh_args)
        # proc = sp.run(['ssh'] + ssh_args)
        # sys.exit(proc.returncode)
    except KeyboardInterrupt:
        pass
    

def is_rpc_server_running():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(1)
            client.connect("127.0.0.1", DEFAULT_IPC_PORT)
        return True 
    except:
        return False

def start_rpc_server():
    server = IPCServerSocket(DEFAULT_IPC_PORT)
    server_thread = server.start()
    return server, server_thread

def connect_to_rpc_server():
    def connect():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', DEFAULT_IPC_PORT))
            
            return sock
        except socket.error:
            return None
    
    socks_client = connect()
    if not socks_client:
        sp.Popen(["rcode-ipc"])
        time.sleep(0.2)

        for _ in range(10):
            try:
                socks_client = connect()
                if socks_client:
                    break
            except socket.error:
                time.sleep(0.5)
    
    return socks_client

def create_session():
    session = {"sid": str(uuid.uuid4()), "key": str(uuid.uuid4())}

    return session

def main():
    session = create_session()
    init_root_dir()
    establish_ssh_connection(session)
    # pass
    # with connect_to_rpc_server() as sock:
    #     if not sock:
    #         print("Error: Failed to connect to RPC server", file=sys.stderr)
    #         sys.exit(1)

    #     # 发送注册消息
    #     register_payload = {
    #         "method": "new_session",
    #         "params": {
    #             "id": str(uuid.uuid4()),
    #             "addr": sock.getsockname()[0],
    #             "hostname": socket.gethostname(),
    #             "key": str(uuid.uuid4())  # 生成一个随机key
    #         }
    #     }
        
    #     establish_ssh_connection(sys.argv[1:], DEFAULT_IPC_PORT)

    

if __name__ == '__main__':
    main() 