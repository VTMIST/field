#!/bin/sh
#
# Startup and shutdown the system
#

start() {

    mount -t proc none /proc
    mount -t tmpfs -o size=4048k,mode=0777,noatime none /tmp
    mkdir -p /tmp/var/cache /tmp/var/lock /tmp/var/log
    mkdir -p /tmp/var/run /tmp/var/spool /tmp/var/tmp
    mkdir -p /tmp/share

    chmod 777 /tmp/share

    chmod 775 /tmp/var/lock
    chgrp lock /tmp/var/lock

    rm -rf /var/lib
    mkdir -p /tmp/var/lib/nfs
    mkdir -p /tmp/var/lib/nfs/v4recovery
    mkdir -p /tmp/var/lib/nfs/rpc_pipefs
    ln -s /tmp/var/lib /var

    mount -o remount,ro,noatime /

    # Only do on EXT2/3 roots.

    rootfs=`grep "^\/dev\/root" /proc/mounts | cut -d " " -f 3`

    if [ "$rootfs" == "ext2" -o "$rootfs" == "ext3" ]; then

        echo "Checking root file system"
        mount -o remount,ro,noatime /
        fsck -y -v /
        rc=$?
        if [ "$rc" -eq "0" ]; then
            echo "No errors reported"
        elif [ "$rc" -eq "1" ]; then
            echo "Passed - errors corrected"
        elif [ "$rc" -eq "2" -o "$rc" -eq "3" ]; then
            echo "Automatic reboot in progress"
            reboot -f
        fi

        if [ $rc -gt 1 ]; then
            echo "Problem during file system check"
            sulogin /dev/console
            echo "Automatic reboot in progress"
            reboot -f
        fi

    fi

    echo "Mounting local files systems"
    mount -o remount,rw,noatime /
    mount -a -t nonfs,nfs4,smbfs,cifs -O no_netdev

    if [ -f /swapfile ]; then
        echo "Mounting swap"
        swapon /swapfile
    fi

    if [ -f /etc/sysctl.conf ]; then
        echo "Setting sysctl parameters"
        sysctl -p
    fi

    echo "Setting hostname"
    hostname -F /etc/hostname

}

stop() {
    echo "Shutting down"

    echo "Sending TERM to remaining processes"
    killall5 -15
    sleep 5
    echo "Sending KILL"
    killall5 -9
    sleep 2

    echo "Enabling PC104"
    sbcctl pc104 on

    echo "Unmounting file systems"
    swapoff -a
    umount -a -r -t ext2,yaffs2,vfat

    if [ -f /sbin/ups-monitor ]; then
        echo "Setting battery system for power off"
        ups-monitor
    fi

}

case $1 in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo $"Usage: $0 {start|stop}"
        exit 1
esac

exit $?

