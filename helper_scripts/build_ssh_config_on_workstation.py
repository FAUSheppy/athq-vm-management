#!/usr/bin/python

import sys
import subprocess
import os
import paramiko

HOSTS = [
    "root@atlantishq.de",
    "root@katzencluster.atlantishq.de",
    "root@atlantis-helsinki.atlantishq.de"
]

BASE_FILE = "~/.ssh/base_config"
MAIN_CONFIG = "~/.ssh/config"

if __name__ == "__main__":

    contents = ""
    for target in HOSTS:

        RUN_CMD = ["ssh", "-t", target , "cd /root/athq-vm-management/; python3 main.py"]
        COPY_CMD = ["ssh", "-t", target, "cat /root/athq-vm-management/ssh_config_for_clients"]

        print("Doing", target, file=sys.stderr)
        out = subprocess.run(RUN_CMD, capture_output=True, universal_newlines=True)
        if out.returncode != 0:
            print("failed (run command)!")
            print(out.stderr)
            sys.exit(1)

        out = subprocess.run(COPY_CMD, capture_output=True, universal_newlines=True)
        if out.returncode != 0:
            print("failed (cat command)!")
            print(out.stderr)
            sys.exit(1)
        
        contents += out.stdout
        contents += "\n"

    with open(os.path.expanduser(BASE_FILE)) as f:
        with open(os.path.expanduser(MAIN_CONFIG), "w") as fout:
            fout.write(f.read())
            fout.write("\n")
            fout.write(contents)
