import socket
import subprocess as sp

# from sshconf import read_ssh_config 
# from os.path import expanduser

def main():
    ssh_remote = "vscode-remote://ssh-remote+{remote_name}{remote_dir}"
    remote_uri = ssh_remote.format(remote_name="debian222", remote_dir="/home/darbula/apps/monitor")
    proc = sp.run(["code22", "--folder-uri", remote_uri])
    print(proc.returncode)

    # out = proc.stdout.read()
    # err = proc.stderr.read()
    # print(proc.stdout)
    # print(proc.stderr)
    pass
    # sshs = read_ssh_config(expanduser("~/.ssh/config"))
    # print("完整的config文件内容:")
    # print(sshs.config)

    # print("\n逐个Host的详细信息:")
    # for host in sshs.hosts():
    #     print(sshs.host(host))
    
if __name__ == "__main__":
    main()
