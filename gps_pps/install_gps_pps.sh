#!/bin/sh
# Install the gps_pps driver

module="/aal-pip/field/bin/gps_pps"
device="/dev/gps_pps"
drvr_major_num="100"
drvr_minor_num="0"

# Remove old device file if it exists
rm -f ${device}
# Remove the module that contains the driver
rmmod ${module} 2> /dev/null 1> /dev/null || true 

# Install the module that contains the driver
insmod ${module}.ko
# Create the dev file
mknod ${device} 'c' ${drvr_major_num} ${drvr_minor_num}
