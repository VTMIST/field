#!/bin/sh

module="gps_pps"
device="/dev/gps_pps"

# Remove old device file if it exists
rm -f ${device}
# Remove the module that contains the driver
rmmod ${module} || true > /dev/null
