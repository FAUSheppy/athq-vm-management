import libvirt
import jinja2

class VM:

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))

    def __init__(self, args, skipVirsh):

        self.hostname = args.get("hostname")
        self.subdomains = args.get("subdomains")
        self.ports = args.get("ports")
        self.check = not args.get("nocheck")
        self.terminateSSL = args.get("terminate-ssl")
        self.network = args.get("network") or "default"
        self.isExternal = args.get("external")
        self.noTerminateACME = args.get("no-terminate-acme")
        self.ansible = not args.get("noansible")
        self.sshOutsidePort = None

        if self.isExternal or skipVirsh:
            self.lease = None
            self.ip = None
        else:
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

    def __hash__(self):
        return hash(self.hostname)

    def __eq__(self, other):
        return self.hostname == other.hostname

    def __gt__(self, other):
        if self.hostname != other.hostname:
            return self.hostname > other.hostname
        return len(str(self.__dict__)) > len(str(other.__dict__))

    def dumpStreamComponents(self):
       
        # port forwarding components #
        components = []
        template = self.environment.get_template("nginx_stream_block.conf.j2")

        for portStruct in self.ports:

            name = str(portStruct.get("name")).replace(" ", "")
            portstring = str(portStruct.get("port")).replace(" ", "")
            port_interfaces = portStruct.get("interfaces")
            assert(port_interfaces is None or type(port_interfaces) == list)
            transparent = portStruct.get("transparent")
            proto = portStruct.get("proto") or "tcp"
            isUDP = proto == "udp"
            proxy_timeout = portStruct.get("proxy_timeout") or "10s"
            extra_content = portStruct.get("extra-content")
            targetportoverwrite = portStruct.get("targetportoverwrite")

            compositeName = "-".join((self.hostname, name, portstring, proto))

            if self.isExternal:
                self.ip = portStruct["ip"]

            component = template.render(targetip=self.ip, udp=isUDP, portstring=portstring,
                                        transparent=transparent, proxy_timeout=proxy_timeout,
                                        comment=compositeName, extra_content=extra_content,
                                        targetportoverwrite=targetportoverwrite,
                                        port_interfaces=port_interfaces)

            components.append(component)

        return components

    def dumpSshFowardsNginx(self):

        components = []
        template = self.environment.get_template("nginx_stream_block.conf.j2")
        if not self.isExternal:
            self.sshOutsidePort = 7000 + int(self.ip.split(".")[-1])
            component = template.render(targetip=self.ip, udp=False,
                                            portstring=self.sshOutsidePort,
                                            targetportoverwrite=7000,
                                            transparent=False, proxy_timeout="24h",
                                            comment="ssh-{}".format(self.hostname))
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

        for subdomain in self.subdomains:

            if subdomain.get("no-terminate-ssl"):
                print("Not terminating TLS for: {}".format(subdomain))

            if type(subdomain) != dict:
                raise ValueError("Subdomain must be object containing 'name' ")

            compositeName = "-".join((self.hostname, subdomain["name"].replace(".","-")))
            targetport = subdomain.get("port") or 80
            
            # build cert group #
            if subdomain.get("cert-group"):
                cert_group_name = subdomain.get("cert-group")
                header_line = "proxy_set_header X-Nginx-Cert-Auth $allow_group_{};".format(cert_group_name)
                cert_optional = True
            else:
                header_line = "proxy_set_header X-Nginx-Cert-Auth false;"
                cert_optional = False

            cert_non_optional = subdomain.get("cert-non-optional") or False

            if subdomain.get("include-subdomains") and not subdomain.get("no-terminate-ssl"):
                raise ValueError("Wildcard Subdomain not supported with SSL Termination")

            component = template.render(targetip=self.ip, targetport=targetport, 
                            servernames=[subdomain["name"]], comment=compositeName,
                            proxy_pass_blob=self.proxy_pass_blob,
                            acme=not self.noTerminateACME,
                            terminate_ssl=not subdomain.get("no-terminate-ssl"),
                            basicauth=subdomain.get("basicauth"),
                            extra_location=subdomain.get("extra-location"),
                            include_subdomains=subdomain.get("include-subdomains"),
                            cert_optional=cert_optional,
                            cert_non_optional=cert_non_optional,
                            http_target_port=subdomain.get("http_target_port"),
                            cert_header_line=header_line)
            components.append(component)

        return components
