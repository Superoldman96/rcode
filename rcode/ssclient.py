import socket
import time
import uuid
import json
HOST = '127.0.0.1'  # 本地主机
PORT = 6954        # 端口号

def client_demo():
    """
    Socket 客户端 Demo，连接到指定主机和端口，并发送消息。
    """
    client_socket = None  # 初始化客户端 socket

    try:
        # 1. 创建 socket 对象
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("客户端 Socket 创建成功")

        # 2. 连接到服务器
        server_address = (HOST, PORT)
        client_socket.connect(server_address)
        print(f"成功连接到 {HOST}:{PORT}")

        open_payload = {
            "id": str(uuid.uuid4()),
            "method": "open_ide",
            "params": {
                "bin": "code",
                "path": "/home/darbula/apps/monitor"
            }
        }

        # 3. 发送数据
        message = json.dumps(open_payload)
        encoded_message = message.encode('utf-8') + b'\x1e'  # 将字符串编码为字节
        client_socket.sendall(encoded_message)  # 发送所有数据
        print(f"已发送消息: {message}")
        res = client_socket.recv(1024)
        print(f"接收到服务器响应: {res.decode('utf-8')}")


        message = '{"hello2": "world", "method": "getname"}'
        encoded_message = message.encode('utf-8')  # 将字符串编码为字节
        client_socket.sendall(encoded_message)  # 发送所有数据
        print(f"已发送消息: {message}")
        

        time.sleep(5)
        client_socket.sendall(b'\x1e')

        res = client_socket.recv(1024)
        print(f"接收到服务器响应2: {res.decode('utf-8')}")



        # (可选) 4. 接收服务器的响应
        # data = client_socket.recv(1024)  # 接收最多 1024 字节的数据
        # decoded_data = data.decode('utf-8') # 将接收到的字节解码为字符串
        # print(f"接收到服务器响应: {decoded_data}")

    except socket.error as e:
        print(f"Socket 错误: {e}")
    finally:
        # 5. 关闭连接
        if client_socket:
            client_socket.close()
            print("客户端 Socket 关闭")

if __name__ == "__main__":
    client_demo()
