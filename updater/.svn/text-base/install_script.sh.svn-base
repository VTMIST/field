#!/bin/sh
# Script: Installs the aal-pip software.
# Assumes all required files are in the
#  /tmp/install/image directory.
# This script is run by updater at boot time if
#  an image file was found in /install.
if [ -e /tmp/install/image ]
then
    if [ -e /aal-pip/field/bin ]
    then
        echo "install_script: /aal-pip/field/bin directory exists"
    else
        mkdir -p /aal-pip/field/bin
        echo "install_script: created /aal-pip/field/bin directory"
    fi
    rm /aal-pip/field/bin/* 2> /dev/null
    echo "install_script: deleted contents of /aal-pip/field/bin directory"
    cp /tmp/install/image/* /aal-pip/field/bin
    echo "install_script: copied application files to /aal-pip/field/bin"
    rm /aal-pip/field/bin/install_script
else
    echo "install_script: nothing to install"
fi
