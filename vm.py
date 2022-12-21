import libvirt
import jinja2

HA_PROXY_STATIC_ACLS = '''
acl is_acme path -i -m beg /.well-known/acme-challenge/
'''

class VM:

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))

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

    def dumpStreamComponents(self):
       
        # port forwarding components #
        components = []
        template = self.environment.get_template("nginx_server_block.conf.j2")

        for portStruct in self.ports:

            name = str(portStruct.get("name")).replace(" ", "")
            portstring = str(portStruct.get("port")).replace(" ", "")
            transparent = portStruct.get("transparent")
            proto = portStruct.get("proto") or "tcp"
            isUDP = proto == "udp"

            compositeName = "-".join((self.hostname, name, portstring, proto))

            component = template.render(targetip=self.ip, udp=isUDP, portstring=portstring,
                                            transparent=transparent)
            components.append(component)

        return components

    def dumpServerComponents(self):

        # https components #
        components = []
        template = self.environment.get_template("nginx_server_block.conf.j2")
        targetport = 80

        if all([type(e) == dict for e in self.subdomains]):
            for subdomain in self.subdomains:
                compositeName = "-".join((self.hostname, subdomain["name"].replace(".","-")))
                targetport = subdomain["port"]
                component = template.render(targetip=self.ip, targetport=targetport, 
                                servernames=[subdomain["name"]], comment=compositeName)
                components.append(component)

        elif any([type(e) == dict for e in self.subdomains]):
            raise ValueError("Mixed subdomains not allowed - must be all complex or all simple")
        else:
            compositeName = "-".join((self.hostname, self.subdomains[0].replace(".","-")))
            component = template.render(targetip=self.ip, targetport=targetport, 
                            servernames=self.subdomains, comment=compositeName)
            components.append(component)

        return components

