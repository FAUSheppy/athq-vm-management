import libvirt
import jinja2

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
        self.proxy_pass_options = args.get("proxy_pass_options")
        self.proxy_pass_blob = ""
        if self.proxy_pass_options:
            self.proxy_pass_blob = "\n".join(self.proxy_pass_options)

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
        template = self.environment.get_template("nginx_stream_block.conf.j2")

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

    def dumpIptables(self, remove=False):

        entries = []
        BASE = "iptables -t mangle -{option} "
        RULE = "PREROUTING -p {proto} -s {ip} {port} -j MARK --set-xmark 0x1/0xffffffff\n"
        PORT_SIMPLE = "--sport {port}"

        option = "A"
        if remove:
            option = "D"

        for portStruct in filter(lambda p: p.get("transparent"), self.ports):

            # port match #
            port = portStruct.get("port")
            partport = PORT_SIMPLE.format(port=port)
            if type(port) == str and "-" in port:
                port = port.replace("-", ":").replace(" ","")
                partport = PORT_SIMPLE.format(port=port)

            entry = BASE.format(option=option)
            entry += RULE.format(ip=self.ip, port=partport, proto=portStruct.get("proto", "tcp"))
            entries.append(entry)

        return entries

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
                                servernames=[subdomain["name"]], comment=compositeName,
                                proxy_pass_blob=self.proxy_pass_blob)
                components.append(component)

        elif any([type(e) == dict for e in self.subdomains]):
            raise ValueError("Mixed subdomains not allowed - must be all complex or all simple")
        else:
            compositeName = "-".join((self.hostname, self.subdomains[0].replace(".","-")))
            component = template.render(targetip=self.ip, targetport=targetport, 
                            servernames=self.subdomains, comment=compositeName,
                            proxy_pass_blob=self.proxy_pass_blob)
            components.append(component)

        return components

