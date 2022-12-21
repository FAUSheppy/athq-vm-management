import json
import vm

ACME_CONTENT = '''
location /.well-known/acme-challenge/ {
    auth_basic off;
    alias /var/www/.well-known/acme-challenge/;
}
'''

if __name__ == "__main__":

    FILE = "vms.json"
    with open(FILE) as f:
        jsonList = json.load(f)
        vmList = []
        for obj in jsonList:
            try:
                vmo = vm.VM(obj)
                vmList.append(vmo)
            except ValueError as e:
                print(e, file=sys.stderr)
       
        with open("./build/stream_include.conf", "w") as f:
            for vmo in vmList:
                [ f.write(c) for c in vmo.dumpStreamComponents()]

        with open("./build/http_include.conf", "w") as f:
            for vmo in vmList:
                [ f.write(c) for c in vmo.dumpServerComponents()]

        with open("./build/acme-challenge.conf", "w") as f:
            f.write(ACME_CONTENT)

        with open("./build/cert.sh", "w") as f:

            f.write("certbot certonly --webroot -w /var/www \\")
            domains = []
            for vmo in vmList:
                for subdomain in vmo.subdomains:
                    if type(subdomain) == dict:
                        domains.append(subdomain["name"])
                    else:
                        domains.append(subdomain)

            for d in set(domains):
                f.write("    -d {} \\".format(d))

            f.write("--rsa-key-size 2048 --expand")
