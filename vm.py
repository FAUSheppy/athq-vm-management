import libvirt

BASE_DOMAIN = "new.atlantishq.de"

HA_PROXY_TEMPLATE_PORT = '''
listen {name}
    bind 0.0.0.0:{port}
    mode {proto}
    timeout connect 4000
    timeout client  180000
    timeout client  180000
    server srv1 {ip}

'''

HA_PROXY_TEMPLATE_SNI = '''
frontend {subdomain}.{basedomain}
    bind 0.0.0.0:80
    bind 0.0.0.0:443 {ssl}
    http-request redirect scheme https unless {{ ssl_fc }}
    default_backend {name}

backend {name}
    server srv1 {ip} check maxconn 20

'''

class VM:

    def __init__(self, args):

        self.hostname = args.get("hostname")
        self.subdomains = args.get("subdomains")
        self.ports = args.get("ports")
        self.terminateSSL = args.get("terminate-ssl")
        self.network = args.get("network") or "default"
        self.lease = self._get_lease_for_hostname()
        self.ip = self.lease.get("ipaddr")

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

        # port forwarding components #
        for pObj in self.ports:
            name = str(pObj.get("name")).replace(" ", "")
            portOrRange = str(pObj.get("port")).replace(" ", "")
            proto = pObj.get("proto") or "tcp"
            compositeName = "-".join((self.hostname, name, portOrRange, proto))

            component = HA_PROXY_TEMPLATE_PORT.format(name=compositeName, port=portOrRange,
                                                      proto=proto, ip=self.ip)
            components.append(component)

        # https components #
        for subdomain in self.subdomains:
            compositeName = "-".join((self.hostname, subdomain.replace(".","-")))

            # check ssl termination #
            ssl = ""
            if self.terminateSSL:
                ssl = "ssl"

            component = HA_PROXY_TEMPLATE_SNI.format(name=compositeName, basedomain=BASE_DOMAIN,
                                                     ip=self.ip, subdomain=subdomain, ssl=ssl)
            components.append(component)

        return components

