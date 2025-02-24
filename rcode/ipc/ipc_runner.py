import argparse
from . import IPCServerSocket, DEFAULT_IPC_PORT

def parse_args():
    parser = argparse.ArgumentParser(description="IPC Server")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="host to listen on (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_IPC_PORT,
        help=f"Port to listen on (default: {DEFAULT_IPC_PORT})",
    )
    parser.add_argument(
        "--max-idle",
        type=int,
        default=600,
        help="Maximum idle time in seconds (default: 600)",
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    server = IPCServerSocket(args.max_idle)
    try:
        server.start(args.host, args.port)
    except KeyboardInterrupt:
        print("\nShutting down IPC server...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
