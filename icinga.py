import jinja2
environment = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))

def createMasterHostConfig(vmList):
    template = environment.get_template("icinga_host.conf.j2") 
    with open("ansible/files/icinga_master_hosts.conf", "w") as f:
        for vmo in vmList:

            if not vmo.check:
                continue

            checkDomains = filter(lambda x: not x.get("nocheck"), vmo.subdomains)
            websites = [ (s["name"], s.get("url")) for s in checkDomains]
            f.write(template.render(hostname=vmo.hostname, address=vmo.ip, websites=websites))

def createMasterServiceConfig(vmList):
    pass

