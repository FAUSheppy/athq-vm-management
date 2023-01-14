import jinja2

def dump_config(vmList):

    password = None
    with open("password.txt") as f:
        password = f.read().strip("\n")

    # dump ansible
    with open("./ansible/hosts.ini", "w") as f:
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
        template = env.get_template("hosts.ini.j2")
        for vmo in set(vmList):
            if vmo.ansible:
                f.write(template.render(hostname=vmo.hostname, ip=vmo.ip))
                f.write("\n")
    
    # dump ansible
    with open("./ansible/files/nsca_server.conf", "w") as f:
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
        template = env.get_template("nsca_server.conf.j2")
        f.write(template.render(vmList=sorted(list(set(filter(lambda x: x.ansible, vmList)))),
                                password=password))
