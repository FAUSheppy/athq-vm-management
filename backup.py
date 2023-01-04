import jinja2
import os
environment = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))

def createBackupScriptStructure(backupList, baseDomain=""):

    rsyncScriptTemplate = environment.get_template("rsync-backup.sh.j2")
    rsyncFilterTemplate = environment.get_template("rsync-filter.txt.j2")

    scriptNames = []
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
        for p in paths:

            if not os.path.isabs(p):
                print("WARNING: Non-absolute path for backup {} (skipping..)".format(p))
                continue
            elif "//" in p:
                print("WARNING: Illegal double-slash in backup path {} (skipping..)".format(p))
                continue
            elif "/" == p:  
                print("WARNING: Root (/) is not allowed as backup path (skipping..)".format(p))
                continue
            else:
                basePaths.append("/{}/".format(p.split("/")[1]))

        # keep order (important!)
        paths = list(set(basePaths)) + [ p.rstrip("/") + "/***" for p in paths ]

        rsyncScript = rsyncScriptTemplate.render(hostname=hostname, token=icingaToken,
                                                 hostname_base=hostnameBase)
        rsyncFilter = rsyncFilterTemplate.render(paths=paths)

        path = "./build/backup/"

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
