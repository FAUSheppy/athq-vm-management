#!/usr/bin/python

import libvirt
import os
import time
import sys
import subprocess
import datetime
import pwd
import grp

BASE_DIR = "/home/backup-atlantis-array/"
BACKUP_USER_NAME = "backup-atlantis-array"
BACKUP_USER = pwd.getpwnam(BACKUP_USER_NAME).pw_uid
BACKUP_GROUP = grp.getgrnam(BACKUP_USER_NAME).gr_gid

def list_running_vms(conn):
    running_vms = []
    for domain_id in conn.listDomainsID():
        domain = conn.lookupByID(domain_id)
        running_vms.append(domain)
    return running_vms

def get_default_network_xml(conn):
    network = conn.networkLookupByName('default')
    return network.XMLDesc()

if __name__ == "__main__":

    # connect to libvirt daemon #
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system')
        sys.exit(1)

    # build date str #
    date_str = datetime.datetime.now().strftime("%y-%m-%d")

    # get running vms #
    running_vms = list_running_vms(conn)

    # dump network #
    default_network_xml = get_default_network_xml(conn)
    network_dir = os.path.join(BASE_DIR, "network")
    os.makedirs(network_dir, exist_ok=True)
    network_path = os.path.join(network_dir, "network-{}.xml".format(date_str))
    with open(network_path, "w") as f:
        f.write(default_network_xml)

    os.chown(network_dir, BACKUP_USER, BACKUP_GROUP)
    os.chown(network_path, BACKUP_USER, BACKUP_GROUP)

    # debug output #
    print("Doing:", [vm.name() for vm in running_vms])

    for vm in running_vms:

        # shut down VM #
        print("Next:", vm.name())
        if not vm.name() == "signal":
            continue

        vm.shutdown()
        grace_time = 1
        while vm.state()[0] != libvirt.VIR_DOMAIN_SHUTOFF:

            if grace_time > 120:
                print("Exeeded maximum shutdown wait for {}".format(vm.name()), file=sys.stderr)
                sys.exit(1)

            print("\rWaiting for '{}' to shutdown ({}/120s)".format(vm.name(), grace_time))
            grace_time += 1
            time.sleep(1)

        # create the backup dir for domain
        safe_dir_xml = os.path.join(BASE_DIR, "{}-xml".format(vm.name()))
        safe_dir_img = os.path.join(BASE_DIR, "{}-img".format(vm.name()))
        os.makedirs(safe_dir_xml, exist_ok=True)
        os.makedirs(safe_dir_img, exist_ok=True)
        os.chown(safe_dir_xml, BACKUP_USER, BACKUP_GROUP)
        os.chown(safe_dir_img, BACKUP_USER, BACKUP_GROUP)
    
        # take xml dump #
        path_xml = os.path.join(safe_dir_xml, "{}-{}.xml".format(vm.name(), date_str))
        with open(path_xml, "w") as f:
            f.write(vm.XMLDesc())
        os.chown(path_xml, BACKUP_USER, BACKUP_GROUP)
    
        # take img #
        image_src_path = "/var/lib/libvirt/images/{}".format(vm.name())
        path_img = os.path.join(safe_dir_img, "{}-{}.img".format(vm.name(), date_str))
        p = subprocess.run(["virt-sparsify", image_src_path, "--compress", path_img])
        if p.returncode != 0:
            print("ERROR: virt-sparsify failed for {}".format(vm.name()), file=sys.stderr)
            vm.start()
            sys.exit(1)
        os.chown(path_img, BACKUP_USER, BACKUP_GROUP)
    
        # start  vm #
        vm.create()
    
        # wait for atlantis-array to collect the backup
        i = 0
        while os.path.isfile(path_img) or os.path.isfile(path_xml):
            print("\rWaiting for array to collect the files ({}s..)".format(i))
            time.sleep(1)
            i += 1
