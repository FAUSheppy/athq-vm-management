#!/usr/bin/python

import libvirt
import os
import sys
import subprocess

BASE_DIR = "/home/backup-atlantis-array/"

def list_running_vms(conn):
    running_vms = []
    for domain_id in conn.listDomainsID():
        domain = conn.lookupByID(domain_id)
        running_vms.append(domain)
    return running_vms

def get_default_network_xml(conn):
    network = conn.networkLookupByName('default')
    return network.XMLDesc()

if __name__ == "__main"__:

    # connect to libvirt daemon #
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system')
        sys.exit(1)

    # build date str #
    date_str = datetime.datetime.now().stftime("%y-%m-%d")

    # get running vms #
    running_vms = list_running_vms(conn)

    # dump network #
    default_network_xml = get_default_network_xml(conn)
    with open(os.path.join(BASE_DIR, "network-{}.xml".format(date_str)), "w") as f:
        f.write(default_network_xml)

    # debug output #
    print("Doing:")
    print([ "  " + vm.name() + "\n" for vm in running_vms])

    for vm in running_vms:

        # shut down VM #
        print("Next:", vm.name())
        vm.shutdown()

        # create the backup dir for domain
        safe_dir_xml = os.path.join(BASE_DIR, vm.name())
        safe_dir_img = os.path.join(BASE_DIR, vm.name())
        os.makedirs(safe_dir_xml, exists_ok=True)
        os.makedirs(safe_dir_img, exists_ok=True)
        os.chown(safe_dir_xml, BACKUP_USER)
        os.chown(safe_dir_img, BACKUP_USER)
    
        # take xml dump #
        path_xml = os.path.join(safe_dir_xml, "{}-{}.xml".format(vm.name(), date_str))
        with open(path_xml, "w") as f:
            f.write(vm.XMLDesc())
        os.chown(path_xml, BACKUP_USER)
    
        # take img #
        image_src_path = "/var/lib/libvirt/images/{}".format(vm.name())
        path_img = os.path.join(safe_dir_img, "{}-{}.img".format(vm.name(), date_str))
        p = subprocess.run(["virt-sparsify", image_src_path, "--compress", path_img])
        if p.return_code != 0:
            print("ERROR: virt-sparsify failed for {}".format(vm.name()), file=sys.stderr)
            vm.start()
            sys.exit(1)
        os.chown(path_img, BACKUP_USER)
    
        # start  vm #
        vm.start()
    
        # wait for atlantis-array to collect the backup
        i = 0
        while os.path.isfile(path_img) or os.path.isfile(path_xml):
            print("\rWaiting for array to collect the files ({}s..)".format(i))
            time.sleep(1)
            i += 1
