#!/bin/bash
for vm in $(virsh list --state-running --name); do
    echo $vm
    virsh shutdown "$vm"
done
while virsh list | grep running; do
    sleep 5
done
