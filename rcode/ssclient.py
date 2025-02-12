import json

from ipc import IPCClientSocket

HOST = '127.0.0.1'  # 本地主机
PORT = 7532        # 端口号

def client_demo():
    try:
        client_socket = IPCClientSocket()
        client_socket.connect((HOST, PORT))
        session_payload = {
            "method": "new_session",
            "params": {
                "hostname": "debian",
                "keyfile": "5b78f900-4470-4460-8490-b7074f9e335c"
            }
        }
        client_socket.write(session_payload)
        data = json.loads(client_socket.read())
        print(data)

        data = data["data"]
        open_payload = {
            "method": "open_ide",
            "params": {
                "sid": data["sid"],
                "skey": data["key"],
                "bin": "code",
                "path": "/home/darbula/apps/monitor"
            }
        }
        print(open_payload)
        client_socket.write(open_payload)
        res = client_socket.read()
        print(res)

        client_socket.close()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    client_demo()
