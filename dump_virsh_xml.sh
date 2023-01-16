#!/bin/bash

BACKUP_NAME=backup_$(date +%Y%m%d)

mkdir -p ./virsh_backup/${BACKUP_NAME}/

virsh dumpxml ths            > ./virsh_backup/${BACKUP_NAME}/ths.xml
virsh dumpxml steam-master   > ./virsh_backup/${BACKUP_NAME}/steam-master.xml
virsh dumpxml usermanagement > ./virsh_backup/${BACKUP_NAME}/usermanagement.xml
virsh dumpxml monitoring     > ./virsh_backup/${BACKUP_NAME}/monitoring.xml
virsh dumpxml typo3-cms      > ./virsh_backup/${BACKUP_NAME}/typo3-cms.xml
virsh dumpxml git            > ./virsh_backup/${BACKUP_NAME}/git.xml
virsh dumpxml backup         > ./virsh_backup/${BACKUP_NAME}/backup.xml
virsh dumpxml vpn            > ./virsh_backup/${BACKUP_NAME}/vpn.xml
virsh dumpxml irc            > ./virsh_backup/${BACKUP_NAME}/irc.xml
virsh dumpxml mail           > ./virsh_backup/${BACKUP_NAME}/mail.xml
virsh dumpxml kathi          > ./virsh_backup/${BACKUP_NAME}/kathi.xml
virsh dumpxml nextcloud-athq > ./virsh_backup/${BACKUP_NAME}/nextcloud-athq.xml
virsh dumpxml web1           > ./virsh_backup/${BACKUP_NAME}/web1.xml
virsh dumpxml kube1          > ./virsh_backup/${BACKUP_NAME}/kube1.xml

virsh net-dumpxml default    > ./virsh_backup/${BACKUP_NAME}/default-network.yml

zip -q -r ./virsh_backup/${BACKUP_NAME}
