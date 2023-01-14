import jinja2
import functools
import os
import subprocess
import json

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./templates"))

def createBackupScriptStructure(backupList, baseDomain=""):


    backupPath = "./build/backup/"
    if not os.path.isdir(backupPath):
        os.mkdir(backupPath)

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
        pathsToOptions = dict()
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
                        pathsToOptions.update({ tmpPath : options })

                fullPaths.append(cur)
                pathsToOptions.update({ cur : options })

        # keep order (important!)
        pathsAll = list(set(basePaths)) + [ p.rstrip("/") + "/***" for p in fullPaths ]

        filterNoHighData = functools.partial(noHighData, hostname, pathsToOptions)
        filterSizeChanged = functools.partial(sizeChanged, hostname, pathsToOptions)
        pathsNoHighData        = list(filter(filterNoHighData, pathsAll))
        pathsOnlyIfSizeChanged = list(filter(filterSizeChanged, pathsAll))
        pathsMinimal           = list(filter(filterSizeChanged, pathsNoHighData))

        rsyncScript = rsyncScriptTemplate.render(hostname=hostname, token=icingaToken,
                                                 hostname_base=hostnameBase)
        
        rsyncFilterAll = rsyncFilterTemplate.render(paths=pathsAll)
        rsyncFilterNoHighData = rsyncFilterTemplate.render(paths=pathsNoHighData)
        rsyncFilterOnlyIfSizeChanged = rsyncFilterTemplate.render(paths=pathsOnlyIfSizeChanged)
        rsyncFilterMinimal = rsyncFilterTemplate.render(paths=pathsMinimal)

        # async icinga config #
        asyncIcingaConf |= { "backup_{}".format(hostnameBase) : 
                                    { "timeout" : "7d", "token" : icingaToken }}

        # write script #
        scriptName = "rsync-backup-{}.sh".format(hostnameBase)
        scriptNames.append(scriptName)

        with open(os.path.join(backupPath, scriptName), "w") as f:
            f.write(rsyncScript)
        os.chmod(os.path.join(backupPath, scriptName), 0o700)

        # write filter #
        filterName = "rsync-filter-{}.txt".format(hostnameBase)
        with open(os.path.join(backupPath, filterName), "w") as f:
            f.write(rsyncFilterAll)

        # compose & write alternative rsync filters #
        alternativeRsyncFilters = [
            ( "size_changed", rsyncFilterOnlyIfSizeChanged ),
            ( "no_high_data", rsyncFilterNoHighData ),
            ( "minimal" , rsyncFilterMinimal )
        ]
        for filterType, render in alternativeRsyncFilters:
            filterType = "rsync-filter-{}-{}.txt".format(hostnameBase, filterType)
            with open(os.path.join(backupPath, filterName), "w") as f:
                f.write(render)

        # endfor #
    
    # write wrapper script #
    wrapperName = "wrapper.sh"
    with open(os.path.join(backupPath, wrapperName), "w") as f:
        for n in scriptNames:
            f.write("./{}".format(n))
            f.write("\n")
    os.chmod(os.path.join(backupPath, wrapperName), 0o700)

    # write async icinga dynamic json in ansible #
    ansibleFilename = "./ansible/files/async-icinga-config-dynamic.json"
    with open(ansibleFilename, "w") as f:
        f.write(json.dumps(asyncIcingaConf))

    # write async icinga services in ansible #
    ansibleFilename = "./ansible/files/async-icinga-services-dynamic.conf"
    icingaServiceTemplate = environment.get_template("async-icinga-services-dynamic.conf.j2")
    with open(ansibleFilename, "w") as f:
        f.write(icingaServiceTemplate.render(asyncIcingaConf=asyncIcingaConf))

# filters #
def noHighData(hostname, pathsToOptions, path):

    if "*" in path:
        return True

    options = pathsToOptions[path]
    return not (options and "highdata" in options)

def sizeChanged(hostname, pathsToOptions, path):

    # keep all generated paths #
    if "*" in path:
        return True

    # if there are no options keep it #
    options = pathsToOptions[path]
    if not options or not "onlyifsizechanged" in options:
        return True

    # check server #
    cmd = ["ssh", hostname,  "-t", "/opt/check_dir_size_for_backup.py", path ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding="utf-8") 
    stdout, stderr = p.communicate()
    if p.wait() != 0:
        raise OSError("ssh commmand for backup size info failed '{}' - '{}'".format(stderr, stdout))

    # parse response #
    result = json.loads(stdout)
    return result["changed"]
