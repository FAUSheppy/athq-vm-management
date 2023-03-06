#!/bin/bash

echo "Doing $1"
test $@ -eq 1
TEST=$(python3 -c "print(int('$TYPE' in ['size_changed', 'no_high_data', 'minimal', ''])^1)")
if [ $TEST -ne 0 ]; then
    echo Bad Filter Option [$TYPE]
    exit 1
fi

# check if we are root
test $(whoami) = root

# mount backup disk
udisksctl unlock --key-file udisk.pass -b /dev/sda1
udisksctl mount -b /dev/dm-2

# pull newest git
cd ~/athq-vm-management
git pull
cd config
git pull
cd ..
cd ansible
git pull
cd ..

# create backup script
eval `ssh-agent`
ssh-add ~/.ssh/sheppymaster
rm -rf ~/athq-vm-management/build/backup/*
python3 main.py --skip-nginx --skip-icinga --skip-ansible --skip-ssh-config --backup

TARGET=/media/root/bd358053-84a3-498c-9109-cc4f4d5c10d8/sheppy/new_server/
rm ${TARGET}rsync-*
cp ~/athq-vm-management/build/backup/* $TARGET
cd $TARGET
pwd
./wrapper.sh $1
