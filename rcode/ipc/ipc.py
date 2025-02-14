import selectors
import socket
import types
import json
import sys
import subprocess as sp
import time
import uuid

from pathlib import Path


DEFAULT_IPC_PORT = 7532
DELIMITER = b"\x1e"

class IPCAuthError(Exception):
    def raw_message(self):
        msg = json.dumps({"code": 401, "message": str(self)})
        return msg.encode("utf-8")

class MessageHandler:
    # 定义为类属性
    AUTH_METHODS = ["open_ide"]
    ANNO_METHODS = ["new_session"]
    RPC_METHODS = AUTH_METHODS + ANNO_METHODS

    def __init__(self):
        self.sessions = {} 

    def handle_message(self, raw_data: bytes, key: selectors.SelectorKey):
        try:
            payload = json.loads(raw_data)
            method_name = payload['method']
            params = payload.get('params', {})

            if 'method' not in payload:
                raise ValueError("Missing required 'method' field in request")
            
            if not hasattr(self, method_name) or method_name not in self.RPC_METHODS:
                raise ValueError(f"Method '{method_name}' not found.")
            
            method_to_call = getattr(self, method_name)
            if method_name not in self.ANNO_METHODS:
                if 'sid' not in params or 'skey' not in params:
                    raise IPCAuthError("Missing authentication credentials (sid, skey)")
                
                sid = params['sid']
                skey = params['skey']
                
                if sid not in self.sessions:
                    raise IPCAuthError(f"Invalid session ID: {sid}")
                
                if self.sessions[sid].key != skey:
                    raise IPCAuthError("Invalid session key")
                
                result = method_to_call(params)
            else:
                result = method_to_call(key.data, params)
            
            response = {"code": 0, "data": result}
            return json.dumps(response).encode("utf-8")
        except json.JSONDecodeError as e:
            response = {"code": 1, "message": f"Invalid JSON format: {str(e)}"}
            return json.dumps(response).encode("utf-8")
        except IPCAuthError as e:
            raise e
        except Exception as e:
            response = {"code": 1, "message": str(e)}
            return json.dumps(response).encode("utf-8")

    def open_ide(self, params: dict):
        valid_bins = ["code", "cursor", "windsurf"]
        if params.get("bin") not in valid_bins:
            raise ValueError(f"Invalid bin: {params['bin']}.")

        if params.get("path") is None:
            raise ValueError("Missing required 'path' field in request")
        
        session = self.sessions[params['sid']]
        remote_name = session.hostname
        remote_dir = params['path']
        is_win = sys.platform == "win32"

        ssh_remote = "vscode-remote://ssh-remote+{remote_name}{remote_dir}"
        ssh_remote = ssh_remote.format(remote_name=remote_name, remote_dir=remote_dir)
        try:
            proc = sp.run([params["bin"], "--folder-uri", ssh_remote], shell=is_win)
        except Exception as e:
            print(e)
            return {"return_code": 1}

        return {"return_code": proc.returncode}

    def new_session(self, data: types.SimpleNamespace, params: dict):
        required_fields = ['hostname', "keyfile"]
        for field in required_fields:
            if field not in params:
                raise ValueError(f"Missing required field: {field}")
            
        keyfile = Path.home() / ".rcode/rssh.keyfile"
        if not keyfile.exists() or keyfile.read_text() != params["keyfile"]:
            raise IPCAuthError(f"Authentication failed")
        
        sid = data.sid
        key = str(uuid.uuid4())
        self.sessions[sid] = types.SimpleNamespace(
            id=sid, 
            addr=data.addr, 
            hostname=params['hostname'], 
            key=key, 
        )

        return {"sid": sid, "key": key}

    def destroy_session(self, sid: str):
        if sid in self.sessions:
            del self.sessions[sid]
            return True
        return False
        


class IPCServerSocket:
    def __init__(self, max_idle: int = 600):
        self.selector = selectors.DefaultSelector()
        self.message_handler = MessageHandler()
        self.running = False
        self.server_socket = None
        self.max_idle = max_idle

    def _accept(self, sock):
        conn, addr = sock.accept()
        conn.setblocking(False)
        data = types.SimpleNamespace(
            addr=addr, 
            inb=b'', 
            outb=b'', 
            sid=str(uuid.uuid4()), 
            last_write=False
        )
        self.selector.register(conn, selectors.EVENT_READ, data=data)

    def _handle_connection(self, key, mask):
        sock = key.fileobj
        data = key.data

        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            print("recv_data:", recv_data)
            if recv_data:
                delimiter_index = recv_data.find(DELIMITER)
                if delimiter_index != -1:
                    raw_data = data.inb + recv_data[:delimiter_index]
                    
                    if delimiter_index < len(recv_data) - 1:
                        data.inb = recv_data[delimiter_index + 1:]
                    else:
                        data.inb = b''
                    
                    try:
                        data.outb = self.message_handler.handle_message(raw_data, key) + DELIMITER
                        self.selector.modify(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)
                    except IPCAuthError as e:
                        data.outb = e.raw_message()
                        data.last_write = True
                        self.selector.modify(sock, selectors.EVENT_WRITE, data=data)
                else:
                    data.inb += recv_data
            else:
                self.message_handler.destroy_session(data.sid)
                self.selector.unregister(sock)
                sock.close()

        if mask & selectors.EVENT_WRITE:
            if data.outb:
                sent = sock.send(data.outb)
                data.outb = data.outb[sent:]

                if not data.outb:
                    if data.last_write:
                        self.selector.unregister(sock)
                        sock.close()
                    else:
                        self.selector.modify(sock, selectors.EVENT_READ, data=data)

    def start(self, host: str, port: int):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen()

        self.server_socket.setblocking(False)
        self.selector.register(self.server_socket, selectors.EVENT_READ, data=None)
        
        self.running = True
        idle = 0
        while self.running:
            events = self.selector.select(timeout=10)
            idle += 10
            clients = len(self.selector.get_map())
            if not events and clients == 1 and idle > self.max_idle:
                break
            
            for key, mask in events:
                idle = 0
                try:
                    if key.data is None:
                        self._accept(key.fileobj)
                    else:
                        self._handle_connection(key, mask)
                except Exception as e:
                    print(e)

    def stop(self):
        if not self.running:
            return

        self.running = False
        if self.server_socket:
            self.selector.unregister(self.server_socket)
            self.server_socket.close()
        # Close all client connections
        for key in list(self.selector.get_map().values()):
            if key.data is not None:  # Client socket
                self.selector.unregister(key.fileobj)
                key.fileobj.close()
        self.selector.close()


class IPCClientSocket:
    def __init__(self, socket_type=socket.AF_INET):
        self.sock = socket.socket(socket_type, socket.SOCK_STREAM)
        self.connected = False
        
    def connect(self, target):
        self.sock.connect(target)
        self.connected = True
        
    def write(self, data):
        if not self.connected:
            raise RuntimeError("Not connected to server")
            
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif not isinstance(data, bytes):
            data = json.dumps(data).encode('utf-8')
            
        if not data.endswith(DELIMITER):
            data += DELIMITER
            
        self.sock.sendall(data)
        
    def read(self):
        if not self.connected:
            raise RuntimeError("Not connected to server")
            
        buffer = b''
        while True:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Connection closed by server")
                
            buffer += chunk
            delimiter_index = buffer.find(DELIMITER)
            
            if delimiter_index != -1:
                message = buffer[:delimiter_index]
                return message
                
    def close(self):
        if self.sock:
            self.sock.close()
            self.connected = False
            self.sock = None

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False 
