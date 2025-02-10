from rcode.ipc import IPCServerSocket, DEFAULT_IPC_PORT

def main():
    server = IPCServerSocket()
    try:
        # 启动 IPC 服务，注意这里为阻塞运行，直到服务停止
        server.start('127.0.0.1', DEFAULT_IPC_PORT)
    except KeyboardInterrupt:
        print("\nShutting down IPC server...")
    finally:
        server.stop()

if __name__ == "__main__":
    main()