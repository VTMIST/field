
#ifndef _GPS_PPS_H
#define _GPS_PPS_H

#include <linux/ioctl.h>

// Sys clock drift measurement structure
struct drift_measurement {
	struct timeval	begin_sys_time;		// sys time at beginning of drift measurement
	struct timeval	end_sys_time;		// sys time at end of drift measurement
	uint32_t		gps_seconds;		// number of GPS seconds between start and end
};

struct gps_pps_status {
	int		time_of_last_sync;	// time of last UTC sync (secs since 1970)
	char	error[32];			// system clock error at last sync
	char  	latitude[32];		// latitude at last sync
	char  	longitude[32];		// longitude at last sync
};

// "Magic" number that ioctl commands are based on
// (picked arbitrarily)
#define GPS_PPS_IOC_MAGIC 0xD7

// Define the driver IOCTL commands the linux way
#define GPS_PPS_IOC_START_DRIFT			_IO(GPS_PPS_IOC_MAGIC, 1)
#define GPS_PPS_IOC_STOP_DRIFT			_IO(GPS_PPS_IOC_MAGIC, 2)
#define GPS_PPS_IOC_GET_DRIFT			_IOR(GPS_PPS_IOC_MAGIC, 3, struct drift_measurement)
#define GPS_PPS_IOC_SET_TIME			_IOW(GPS_PPS_IOC_MAGIC, 4, struct timeval)
#define GPS_PPS_IOC_GET_TIME			_IOR(GPS_PPS_IOC_MAGIC, 5, struct timeval)
#define GPS_PPS_IOC_START_PSEUDO_PPS	_IO(GPS_PPS_IOC_MAGIC, 6)
#define GPS_PPS_IOC_SET_PROC_STATUS		_IOW(GPS_PPS_IOC_MAGIC, 7, struct gps_pps_status)
#define GPS_PPS_IOC_MAX_NR			7

#endif //_GPS_PPS_H
