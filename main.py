import json
import vm

if __name__ == "__main__":

    FILE = "vms.json"
    with open(FILE) as f:
        jsonList = json.load(f)
        vmList = [ vm.VM(obj) for obj in jsonList ]
        
        for vmo in vmList:
            [ print(c) for c in vmo.dumpHAProxyComponents()]
