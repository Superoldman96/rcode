#!/usr/bin/env python3

import argparse
import subprocess as sp
import sys
import socket
import time
import uuid
import json

from rcode.ipc import IPCServerSocket, DEFAULT_IPC_PORT, DELIMITER

def establish_ssh_connection(args, tunnel_port):
    sid = str(uuid.uuid4())


    ssh_cmd = ['ssh']
    
    # Add reverse tunnel
    ssh_cmd.extend(['-R', f'{tunnel_port}:localhost:{tunnel_port}'])
    
    # Check for -R in arguments
    for i, arg in enumerate(args):
        if arg == '-R' or (arg.startswith('-') and 'R' in arg):
            print("Error: -R option is not supported in rssh as the tunnel is automatically established", 
                  file=sys.stderr)
            sys.exit(1)
    
    # Find the host argument - it's the first argument that doesn't start with '-'
    # and isn't preceded by an option that takes a parameter
    host = None
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
            
        if arg.startswith('-'):
            # List of SSH options that take a parameter
            if arg in ['-b', '-c', '-D', '-E', '-e', '-F', '-I', '-i', '-L', '-l', 
                      '-m', '-O', '-o', '-p', '-Q', '-S', '-W', '-w']:
                skip_next = True
            continue
        else:
            host = arg
            args_before_host = args[:i]
            args_after_host = args[i+1:]
            break
    
    if not host:
        print("Error: No host specified", file=sys.stderr)
        sys.exit(1)
    
    # Construct the final command
    ssh_cmd.extend(args_before_host)
    ssh_cmd.append(host)
    
    # Inject RSSH_HOSTNAME into the remote environment
    if args_after_host:
        remote_command = f'export RSSH_HOSTNAME={host}; {" ".join(args_after_host)}'
    else:
        remote_command = f'export RSSH_HOSTNAME={host}; exec $SHELL'
    
    ssh_cmd.append(remote_command)
    
    try:
        print(ssh_cmd)
        sp.run(ssh_cmd, shell=True)
    except KeyboardInterrupt:
        print("\nSSH connection terminated.")

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

def main():
    with connect_to_rpc_server() as sock:
        if not sock:
            print("Error: Failed to connect to RPC server", file=sys.stderr)
            sys.exit(1)

        # 发送注册消息
        register_payload = {
            "method": "new_session",
            "params": {
                "id": str(uuid.uuid4()),
                "addr": sock.getsockname()[0],
                "hostname": socket.gethostname(),
                "key": str(uuid.uuid4())  # 生成一个随机key
            }
        }
        
        # 发送注册消息
        message = json.dumps(register_payload).encode('utf-8') + DELIMITER
        sock.sendall(message)
        
        # 等待响应
        response = sock.recv(1024)
        if response:
            response_data = json.loads(response.decode('utf-8').rstrip('\x1e'))
            if response_data.get('code') != 0:
                print(f"Registration failed: {response_data.get('message')}")
                return None
        
        establish_ssh_connection(sys.argv[1:], DEFAULT_IPC_PORT)

    

if __name__ == '__main__':
    main() 