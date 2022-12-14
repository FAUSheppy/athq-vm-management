import jinja2
import os
import json

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))

def createBackupScriptStructure(backupList, baseDomain=""):

    rsyncScriptTemplate = environment.get_template("rsync-backup.sh.j2")
    rsyncFilterTemplate = environment.get_template("rsync-filter.txt.j2")

    scriptNames = []
    asyncIcingaConf = {}
    for backup in backupList:

        hostnameBase = backup["hostname"]
        if baseDomain:
            hostname = "{}.{}".format(hostnameBase, baseDomain.lstrip("."))
        else:
            hostname = hostnameBase

        paths = backup["paths"]
        icingaToken = backup["token"]

        if not hostname.replace(".","").isalnum():
            print("Warning: Backup hostname is not alphanum: '{}'".format(hostname))
            continue

        # add base paths for rsync filter (e.g. /var/ for /var/lib/anything/)
        # because we use - /** for excluding anything else #
        basePaths = []
        fullPaths = []
        for p in paths:

            cur = p
            options = None
            if type(p) == dict:
                cur = p["path"]
                options = p["options"]

            if not os.path.isabs(cur):
                print("WARNING: Non-absolute path for backup {} (skipping..)".format(p))
                continue
            elif "//" in cur:
                print("WARNING: Illegal double-slash in backup path {} (skipping..)".format(p))
                continue
            elif "/" == cur:  
                print("WARNING: Root (/) is not allowed as backup path (skipping..)".format(p))
                continue
            else:
                tmpPath = "/"
                for level in cur.split("/")[:-2]:
                    if not level:
                        continue
                    else:
                        tmpPath += "{}/".format(level)
                    if not tmpPath == "/":
                        basePaths.append(tmpPath)

                fullPaths.append(cur)

        # keep order (important!)
        paths = list(set(basePaths)) + [ p.rstrip("/") + "/***" for p in fullPaths ]

        rsyncScript = rsyncScriptTemplate.render(hostname=hostname, token=icingaToken,
                                                 hostname_base=hostnameBase)
        rsyncFilter = rsyncFilterTemplate.render(paths=paths)

        path = "./build/backup/"

        # async icinga config #
        asyncIcingaConf |= { "backup_{}".format(hostnameBase) : 
                                    { "timeout" : "7d", "token" : icingaToken }}

        # write script #
        scriptName = "rsync-backup-{}.sh".format(hostnameBase)
        scriptNames.append(scriptName)
        with open(os.path.join(path, scriptName), "w") as f:
            f.write(rsyncScript)
        os.chmod(os.path.join(path, scriptName), 0o700)

        # write filter #
        filterName = "rsync-filter-{}.txt".format(hostnameBase)
        with open(os.path.join(path, filterName), "w") as f:
            f.write(rsyncFilter)

        # endfor #
    
    # write wrapper script #
    wrapperName = "wrapper.sh"
    with open(os.path.join(path, wrapperName), "w") as f:
        for n in scriptNames:
            f.write("./{}".format(n))
            f.write("\n")
    os.chmod(os.path.join(path, wrapperName), 0o700)

    # write async icinga dynamic json in ansible #
    ansibleFilename = "./ansible/files/async-icinga-config-dynamic.json"
    with open(ansibleFilename, "w") as f:
        f.write(json.dumps(asyncIcingaConf))

    # write async icinga services in ansible #
    ansibleFilename = "./ansible/files/async-icinga-services-dynamic.conf"
    icingaServiceTemplate = environment.get_template("async-icinga-services-dynamic.conf.j2")
    with open(ansibleFilename, "w") as f:
        f.write(icingaServiceTemplate.render(asyncIcingaConf=asyncIcingaConf))
