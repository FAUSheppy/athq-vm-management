import libvirt

HA_PROXY_TEMPLATE = '''
listen {name}
    bind 0.0.0.0:{port}
    mode {proto}
    timeout connect 4000
    timeout client  180000
    timeout client  180000
    server srv1 {ip}
'''

class VM:

    def __init__(self, args):

        self.hostname = args.get("hostname")
        self.subdomains = args.get("subdomains")
        self.ports = args.get("ports")
        self.network = args.get("network") or "default"
        self.lease = _get_lease_for_hostname()
        self.ip = lease.get("ipaddr")

    def _get_lease_for_hostname(self):
        
        with libvirt.open() as con:
            network = con.networkLookupByName(self.network)
            leases = network.DHCPLeases()
            for l in leases:
                if l.get("hostname") == self.hostname:
                    return l
        
        raise ValueError("Hostname {} doesn't have a DHCP lease".format(self.hostname))

    def dumpHAProxyComponents(self):
            
        components = []
        for pObj in self.ports:
            name = str(pObj.get("name")).replace(" ", "")
            portOrRange = pObj.get("port").replace(" ", "")
            proto = pObj.get("proto") or "tcp"
            compositeName = "-".join((self.hostname, name, portOrRange, proto))

            component = HA_PROXY_TEMPLATE.format(name=compositeName, port=port,
                                                 proto=proto, ip=self.ip)
            components.append(component)

        return components

