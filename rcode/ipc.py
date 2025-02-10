import selectors
import socket
import types
import json

from rcode import run_loacl


DELIMITER = b"\x1e"

class MessageHandler:
    def __init__(self):
        self.clents_info = {}
        self.rpc_methods = ["_open_ide", "_register_client"]

    def handle_message(self, raw_data: bytes):
        try:
            payload = json.loads(raw_data)
            print("payload:", payload)

            if 'method' not in payload:
                raise ValueError("Missing required 'method' field in request")
            
            method_name = "_" + payload['method']
            params = payload.get('params', {}) 

            if not hasattr(self, method_name) or method_name not in self.rpc_methods:
                raise ValueError(f"Method '{method_name}' not found.")
            
            method = getattr(self, method_name)
            result = method(params)
            
            response = {"code": 0, "data": result}
            return json.dumps(response).encode("utf-8")
        except json.JSONDecodeError as e:
            response = {"code": 1, "message": f"Invalid JSON format: {str(e)}"}
            return json.dumps(response).encode("utf-8")
        except Exception as e:
            response = {"code": 1, "message": str(e)}
            return json.dumps(response).encode("utf-8")

    def _open_ide(self, payload: dict):
        valid_bins = ["code", "cursor"]
        if payload.get("bin") not in valid_bins:
            raise ValueError(f"Invalid bin: {payload['bin']}.")

        if payload.get("path") is None:
            raise ValueError("Missing required 'path' field in request")
        
        run_loacl(
            dir_name=payload["path"], 
            remote_name=payload.get("host", "debian"),
            shortcut_name=None,
            open_shortcut_name=None,
            is_cursor=payload.get("is_cursor", payload["bin"] != "code")
        )
        
        print("调用 open_ide 方法，参数:", payload)
        return f"open_ide called with: {payload}"

    def _register_client(self, payload: dict):
        # 注册客户端的逻辑
        print("调用 register_client 方法，参数:", payload)
        return f"register_client called with: {payload}"


class IPCServerSocket:
    def __init__(self):
        self.selector = selectors.DefaultSelector()
        self.message_handler = MessageHandler()
        self.running = False
        self.server_socket = None

    def _accept(self, sock):
        conn, addr = sock.accept()
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.selector.register(conn, events, data=data)

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
                    data.outb = self.message_handler.handle_message(raw_data) + DELIMITER
                
                else:
                    data.inb += recv_data

            else:
                self.selector.unregister(sock)
                sock.close()

        if mask & selectors.EVENT_WRITE:
            if data.outb:
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def start(self, host: str, port: int):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen()

        self.server_socket.setblocking(False)
        self.selector.register(self.server_socket, selectors.EVENT_READ, data=None)
        
        self.running = True
        while self.running:
            events = self.selector.select(timeout=10)
            if not events and len(self.selector.get_map()) == 1:
                self.stop()
                print("没有客户端连接，停止服务器")
                break

            for key, mask in events:
                if key.data is None:
                    self._accept(key.fileobj)
                else:
                    self._handle_connection(key, mask)

    def stop(self):
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

