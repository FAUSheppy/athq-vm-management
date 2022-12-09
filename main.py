import json

if __name__ == "__main__":

    FILE = "vms.json"
    with open(FILE) as f:
        jsonList = json.load(f)
        vmList = [ VM(obj) for obj in jsonList ]
        
        for vm in vmList:
            print(vmList.dumpHAProxyComponents())
