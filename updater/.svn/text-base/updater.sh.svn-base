#!/bin/sh
# Script: Perform an update if an
#  image.tar.gz file and a matching md5 checksum file
#  exist in the /install directory
#  
# Updating consists of extracting the image.tar.gz to the
#  /tmp/install directory and then executing the
#  the 'install_script' that was extracted.  The tarball
#  also contains all the other files required for the update.
# After the update is completed, all the update files, including
#  the original image.tar.gz and md5 file are deleted.
# This script should be run at boot time.

start() {
    if [ ! -e /install ]
    then
        echo "updater: /install directory does not exist"
        exit 0
    fi
    if [ ! -f /install/image.tar.gz ]
    then
        echo "updater: no /install/image.tar.gz to install"
        exit 0
    fi
    if [ ! -f /install/image.tar.gz.md5 ]
    then
        echo "updater: /install/image.tar.gz.md5 file is missing"
        rm -f /install/image.tar.gz
        exit 0
    fi
    cd /install
    if md5sum -c /install/image.tar.gz.md5
    then
        echo "updater: valid /install/image.tar.gz found"
    else
        echo "updater: md5 checksum does not match the image file"
        rm -f /install/image.tar.gz
        rm -f /install/image.tar.gz.md5
        exit 0
    fi
    
    # image and md5 exist and are valid
    mkdir -p /tmp/install
    echo "updater: /tmp/install directory created"
    # copy the tar file to /tmp/install
    cp /install/image.tar.gz /tmp/install
    echo "updater: /install/image.tar.gz copied to /tmp/install"
    cd /tmp/install
    # extract the tarball to /tmp/install/image
    tar -xzf image.tar.gz
    echo "updater: /tmp/install/image.tar.gz extracted to /tmp/install/image "
    # copy the md5 file to /tmp/install/image for use as an identifier
    cp /install/image.tar.gz.md5 /tmp/install/image    
    # clean up /tmp/install
    rm /tmp/install/image.tar.gz
    rm /install/image.tar.gz
    rm /install/image.tar.gz.md5
    cd /tmp/install/image
    # execute install_script in /tmp/install/image
    if [ -f install_script ]
    then
        echo "updater: executing install_script from /tmp/install/image"
        /tmp/install/image/install_script
    else
        echo "updater: no install_script in /tmp/install/image"
    fi
    # clean up /tmp
    cd /tmp
    rm /tmp/install/image/*
    rmdir /tmp/install/image
    rmdir /tmp/install/

}
case "$1" in
  start)
    start
        ;;
  stop)
        ;;
  restart)
        ;;
  *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac

exit 0
