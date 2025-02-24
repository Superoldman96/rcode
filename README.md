## Rcode

This repo is fork from [code-connect](https://github.com/chvolkmann/code-connect)
~~Thanks for this cool repo.

https://user-images.githubusercontent.com/1651790/172983742-b27a3fe0-2704-4fc8-b075-a6544783443a.mp4


## What changed

1. PyPI
2. support local open remote dir command `rcode ${ssh_name} ${ssh_dir}`
3. support cursor to open remote dir command `rcursor ${ssh_name} ${ssh_dir}`
4. you can also open dir from remote to local `cursor` just `cursor ${dir_name}`

## INFO

1. pip3 install rcode (or clone it pip3 install .)
2. ~~install socat like: (sudo yum install socat)~~
3. just `rcode file` like your VSCode `code .`
4. or use cursor just `cursor .`
5. local open remote use rcode if you use `.ssh/config` --> `rcode remote_ssh ~/test`
6. local open latest remote `.ssh/config` --> `rcode -l or rcode --latest`
7. add shortcut_name `rcode s ~/abc -sn abc` then you can use `rcode -os abc` to open this dir quickly
8. support cursor to open remote dir command `rcursor ${ssh_name} ${ssh_dir}`
9. Connect to your SSH server with `rssh`, and you can run `rcode/rcursor` on the server to launch VS Code/Cursor, even if they are not running.

> Note:
> - If using traditional SSH connection, be sure to [connect to the remote host](https://code.visualstudio.com/docs/remote/ssh#_connect-to-a-remote-host) first before typing any `rcode` in the terminal
> - We may want to add `~/.local/bin` in to your `$PATH` in your `~/.zshrc` or `~/.bashrc` to enable `rcode` being resolved properly
> ```diff
> - export PATH=$PATH:/usr/local/go/bin
> + export PATH=$PATH:/usr/local/go/bin:~/.local/bin
> ```

## Remote Development with RSSH

RSSH enables seamless remote development by allowing you to launch VS Code/Cursor on your local machine while working with files on a remote server. It works by:

1. Creating a secure SSH tunnel between your local machine and remote server
2. Setting up IPC (Inter-Process Communication) sockets for command transmission
3. Managing remote sessions with unique identifiers and keys

https://github.com/user-attachments/assets/41a44915-4714-4fce-8705-a1550921b2f3

### Usage

1. Connect to remote server using `rssh`:

RSSH is designed to be fully compatible with SSH parameters, with the exception of the -R and -T options, which are not allowed when using RSSH.

```bash
rssh your-remote-server
```

All standard SSH parameters can be used with rssh, except -R and -T.

2. On the remote server, you can now use:
```bash
rcode .      # Launch VS Code
rcursor .    # Launch Cursor
```

### Using `ssh-wrapper`

If you'd like to use rssh as a drop-in replacement for ssh, you can utilize the provided ssh-wrapper. By adding an alias in your shell configuration file (e.g., ~/.bashrc or ~/.zshrc), you can override the ssh command:

```shell
alias ssh="ssh-wrapper"
```

With this alias in place, when you use ssh, it will invoke ssh-wrapper. To activate rssh, include the --rssh parameter:

```shell
ssh --rssh your-remote-server
```

If you do not include the --rssh parameter, it will behave as the default ssh command.

### How It Works

1. When you connect with `rssh`:
   - Generates a unique session ID and key
   - Creates an SSH tunnel for IPC communication
   - Sets up environment variables on the remote server

2. When running `rcode`/`rcursor` on the remote:
   - Communicates with the local IDE through the IPC socket
   - Automatically launches the appropriate IDE on your local machine
   - Opens the remote directory in your IDE

### Advanced Options

- Custom IPC host: `rssh --host <host> your-remote-server`
- Custom IPC port: `rssh --port <port> your-remote-server`

