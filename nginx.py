import jinja2
import json

ACME_CONTENT = '''
location /.well-known/acme-challenge/ {
    auth_basic off;
    alias /var/www/.well-known/acme-challenge/;
}
'''

def dump_config(vmList, masterAddress):

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

        f.write("    -d {} \\\n".format(masterAddress))
        for d in set(domains):
            if d == masterAddress:
                continue
            f.write("    -d {} \\\n".format(d))

        f.write("--rsa-key-size 2048 --expand")

    with open("/etc/nginx/nginx.conf", "w") as f:

        with open("./config/nginx.json") as j:
            nginxJson = json.load(j)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))
            template = env.get_template("nginx.conf.j2")
            content = template.render(nginxJson)

            f.write(content)