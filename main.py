import json
import vm
import sys
import jinja2
import icinga

ACME_CONTENT = '''
location /.well-known/acme-challenge/ {
    auth_basic off;
    alias /var/www/.well-known/acme-challenge/;
}
'''

if __name__ == "__main__":

    password = None
    with open("password.txt") as f:
        password = f.read().strip("\n")

    FILE = "./config/vms.json"
    with open(FILE) as f:
        jsonList = json.load(f)
        vmList = []
        for obj in jsonList:
            try:
                vmo = vm.VM(obj)
                vmList.append(vmo)
            except ValueError as e:
                print(e, file=sys.stderr)

        with open("/etc/nginx/iptables.sh", "w") as f:
            f.write("ip route add local 0.0.0.0/0 dev lo table 100\n")
            f.write("ip rule add fwmark 1 lookup 100\n")
            for vmo in vmList:
                [ f.write(c) for c in vmo.dumpIptables()]

        with open("/etc/nginx/iptables-clear.sh", "w") as f:
            f.write("ip route delete local 0.0.0.0/0 dev lo table 100\n")
            f.write("ip rule delete fwmark 1 lookup 100\n")
            for vmo in vmList:
                [ f.write(c) for c in vmo.dumpIptables(remove=True)]

        with open("/etc/nginx/stream_include.conf", "w") as f:
            for vmo in vmList:
                [ f.write(c) for c in vmo.dumpStreamComponents()]
            for vmo in set(vmList):
                [ f.write(c) for c in vmo.dumpSshFowardsNginx()]

        with open("/etc/nginx/http_include.conf", "w") as f:
            for vmo in vmList:
                [ f.write(c) for c in vmo.dumpServerComponents()]

        with open("/etc/nginx/acme-challenge.conf", "w") as f:
            f.write(ACME_CONTENT)

        with open("/etc/nginx/cert.sh", "w") as f:

            f.write("certbot certonly --webroot -w /var/www \\\n")
            domains = []
            for vmo in vmList:
                for subdomain in vmo.subdomains:
                    if vmo.noTerminateACME:
                        print("Not terminating ACME for: {}".format(subdomain))
                        continue
                    if type(subdomain) == dict:
                        domains.append(subdomain["name"])
                    else:
                        domains.append(subdomain)

            for d in set(domains):
                f.write("    -d {} \\\n".format(d))

            f.write("--rsa-key-size 2048 --expand")

        with open("/etc/nginx/nginx.conf", "w") as f:

            with open("./config/nginx.json") as j:
                nginxJson = json.load(j)
                env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
                template = env.get_template("nginx.conf.j2")
                content = template.render(nginxJson)

                f.write(content)
        
        # dump icinga master
        icinga.createMasterHostConfig(vmList)

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
            f.write(template.render(vmList=set(filter(lambda x: x.ansible, vmList)),
                                    password=password))
