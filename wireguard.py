import jinja2
import subprocess
import os

key_cache_dir = ".wireguard_keys/"

def generate_wireguard_keypair(hostname):

    # create & sanity check filename & create dir #
    assert(hostname.replace(".", "").isalnum())
    filename = os.path.join(key_cache_dir, hostname)
    os.makedirs(key_cache_dir, exist_ok=True)

    # return cache if exists #
    if os.path.isfile(filename):
        with open(filename) as key_file:
            return key_file.read().strip("\n").split(" ")

    # otherwise generate private & public key #
    private_key = subprocess.check_output(['wg', 'genkey']).strip()
    public_key = subprocess.check_output(['wg', 'pubkey'], input=private_key).strip()

    # encode
    private_key = private_key.decode('utf-8')
    public_key = public_key.decode('utf-8')

    # save in key cache #
    with open(filename, "w") as key_file:
        key_file.write(private_key)
        key_file.write(" ")
        key_file.write(public_key)

    return private_key, public_key


def dump_config(vm_list):

    vms_sorted_by_ip = sorted(vm_list, key=lambda x: x.ip)
    clients = []

    for vmo in vms_sorted_by_ip:

        private_key, public_key = generate_wireguard_keypair(vmo.hostname)
        clients.append({
            "name" : vmo.hostname,
            "private_key" : private_key
            "public_key" : public_key
        })

    # dump wireguard vars for ansible #
    with open("./ansible/vers/wireguard.yaml", "w") as f:
        pass

    # dump hypervisor config #
    with open("/etc/wireguard/hypervisor.conf") as f:
        pass
