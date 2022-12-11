import json
import vm

if __name__ == "__main__":

    FILE = "vms.json"
    print(vm.HA_PROXY_STATIC_ACLS)
    with open(FILE) as f:
        jsonList = json.load(f)
        vmList = [ vm.VM(obj) for obj in jsonList ]
        
        for vmo in vmList:
            [ print(c) for c in vmo.dumpHAProxyComponents()]

