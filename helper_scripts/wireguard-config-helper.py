import subprocess
import json
import os
from pathlib import Path
import configparser
import ipaddress

LINK_BASE = f"10.0.{len(EXISTING_HOSTS)+10}.1/32"
LINK_BASE_PEER = f"10.0.{len(EXISTING_HOSTS)+10}.2/32"
PORT_BASE = 51820 + len(EXISTING_HOSTS)

MASTER_CONFIG = """[Interface]
PrivateKey = {local_private}
Address = {local_address}

[Peer]
Endpoint = {peer_endpoint}
PublicKey = {peer_public}
AllowedIPs = {", ".join(peer_allowed_ips)}
"""

PEER_CONFIG = f"""[Interface]
PrivateKey = {peer_private}
Address = {peer_address}

[Peer]
PublicKey = {local_public}
AllowedIPs = {", ".join(peer_allowed_ips)}
"""

def create_wireguard_config_pair(
    new_host: str,
    old_host: str,
    new_host_allowed_ips: list[str],
    old_host_allowed_ips,
    old_host_public_key,
    old_host_private_key,
    output_dir: str = "./tmp"
):

    # Validate input subnet
    try:
        ipaddress.IPv4Interface(local_address)
    except ValueError as e:
        raise ValueError(f"Invalid IP address: {local_address}") from e

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate key pairs
    local_private, local_public = generate_keypair()
    peer_private, peer_public = generate_keypair()

    new_host = MASTER_CONFIG.format(
        local_private = local_private,
        local_address = LINK_BASE,
        local_public = local_public,
        peer_endpoint = old_host,
        peer_public = old_host_public_key,
        peer_allowed_ips = [LINK_BASE_PEER, old_host_allowed_ips],

    )
    old_host = PEER_CONFIG.format(
        peer_private = old_host_private_key,
        peer_address = LINK_BASE_PEER,
        local_public= local_public,
        peer_allowed_ips = [LINK_BASE, new_host_subnet]
    )

    old_host_file = Path(output_dir) / f"{new_host}_local.conf"
    new_host_file = Path(output_dir) / f"{new_host}_peer.conf"

    new_host_file.write_text(new_host)
    old_host_file.write_text(old_host)

    return str(local_file), str(peer_file)

def generate_wireguard_keys():

    private_key = subprocess.check_output(["wg", "genkey"]).strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()

    return private_key.decode(), public_key.decode()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="WireGuard utility script")
    
    parser.add_argument("--new-host", help="Hostname or IP of the new host")
    parser.add_argument("--new-host-subnet", type=ipaddress.IPv4Network, help="Subnet of new host")
    parser.add_argument("--write", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--allow-overwrite", action=argparse.BooleanOptionalAction, default=False)

    args = parser.parse_args()

    configs = {}

    for host in EXISTING_HOSTS:
        fetch_conf_files(host)
        configs |= load_all_confs(host)

    # output current state #
    print(json.dumps(configs, indent=2))

    if args.new_host and args.new_host_subnet:

        # TODO get keys from old host
        create_wireguard_config_pair(LINK_BASE, new_host) #TODO
