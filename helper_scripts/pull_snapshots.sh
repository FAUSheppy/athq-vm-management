#!/bin/bash
if ssh backup-atlantis-array@atlantishq.de [[ -e /home/backup-atlantis-array/lock.rsync ]]; then
    echo "Lockfile found. Waiting 10s.."
    sleep 10
else
    rsync backup-atlantis-array@atlantishq.de:/home/backup-atlantis-array/\* . -rP \
            --remove-source-files    
fi
