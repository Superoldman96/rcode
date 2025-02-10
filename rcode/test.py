import socket

from sshconf import read_ssh_config 
from os.path import expanduser

def main():
    sshs = read_ssh_config(expanduser("~/.ssh/config"))
    print("完整的config文件内容:")
    print(sshs.config)

    print("\n逐个Host的详细信息:")
    for host in sshs.hosts():
        print(sshs.host(host))
    
if __name__ == "__main__":
    main()
