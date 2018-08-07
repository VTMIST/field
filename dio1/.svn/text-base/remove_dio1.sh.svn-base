#!/bin/sh

module="dio1"
device="/dev/dio1"

# Remove old device file if it exists
rm -f ${device}
# Remove the module that contains the driver
rmmod ${module} || true 2> /dev/null
