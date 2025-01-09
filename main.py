import json
import os
import argparse
import vm
import sys
import jinja2
import icinga
import backup
import nginx
import pyansible

MASTER_ADDRESS = "atlantishq.de"

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='AtlantisHQ VM Management Script',
                                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--backup",          action="store_const", default=False, const=True)
    parser.add_argument("--skip-ansible",    action="store_const", default=True, const=False)
    parser.add_argument("--skip-nginx",      action="store_const", default=True, const=False)
    parser.add_argument("--skip-icinga",     action="store_const", default=True, const=False)
    parser.add_argument("--skip-ssh-config", action="store_const", default=True, const=False)
    parser.add_argument("--do-nginx-map-cert-manager", action="store_const", default=False, const=True)
    parser.add_argument("--backup-no-async-icinga", action="store_const", default=False, const=True)
    args = parser.parse_args()

    FILE = "./config/vms.json"
    vmList = []
    skipVirsh = not any([args.skip_ansible, args.skip_nginx, 
                         args.skip_icinga, args.skip_ssh_config])

    # set master address #
    OPTIONAL_MASTER_ADDRESS_FILE="master-address.txt"
    if os.path.isfile(OPTIONAL_MASTER_ADDRESS_FILE):
        with open(OPTIONAL_MASTER_ADDRESS_FILE) as f:
            MASTER_ADDRESS = f.read().strip()

    with open(FILE) as f:
        jsonList = json.load(f)
        for obj in jsonList:
            try:
                vmo = vm.VM(obj, skipVirsh)
                vmList.append(vmo)
            except ValueError as e:
                print(e, file=sys.stderr)
       
    # dump nginx config #
    if args.skip_nginx:
        nginx.dump_config(vmList, MASTER_ADDRESS)
        nginx.check_transparent_proxy_loader()

    # dump icinga master
    if args.skip_icinga:
        icinga.createMasterHostConfig(vmList)

    # dump ansible
    if args.skip_ansible:
        pyansible.dump_config(vmList)

    # dump direct connect ssh-config
    if args.skip_ssh_config:
        with open("./ssh_config_for_clients", "w") as f:
            for vmo in filter(lambda x: x.sshOutsidePort, set(vmList)):
                f.write("Host {}\n".format(vmo.hostname + "." + MASTER_ADDRESS))
                f.write("    Port {}\n".format(vmo.sshOutsidePort))
                f.write("    User root\n")
                f.write("\n")

    # backup #
    try:
        with open("./config/backup.json") as f:
            backup.createBackupScriptStructure(json.load(f), baseDomain=MASTER_ADDRESS,
                                               icingaOnly=not args.backup,
                                               backup_no_async_icinga=args.backup_no_async_icinga)
    except json.decoder.JSONDecodeError as e:
        print("WARNING: Failed loading backup.json - either empty or invalid json!", file=sys.stderr)
        print(e, file=sys.stderr)

    # copy nginx maps #
    if not args.backup and args.do_nginx_map_cert_manager:
        os.system("rsync templates/nginx_maps.j2 root@192.168.122.104:/data/certificate-manager/")
