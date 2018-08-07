
#ifndef _DIO1_H
#define _DIO1_H

#include <linux/ioctl.h>

// Struct used to read a DIO1 bit value
struct bit_info {
	int		number;
	int		value;
	int		dir;	// 0 is input, 1 is output
};


// "Magic" number that ioctl commands are based on
// (picked arbitrarily)
#define DIO1_IOC_MAGIC 0xD8

// Define the driver IOCTL commands the linux way
#define DIO1_IOC_SET_BIT_DIR	_IOW(DIO1_IOC_MAGIC, 1, struct bit_info)
#define DIO1_IOC_GET_BIT_DIR	_IOWR(DIO1_IOC_MAGIC, 2, struct bit_info)
#define DIO1_IOC_SET_BIT_VALUE	_IOW(DIO1_IOC_MAGIC, 3, struct bit_info)
#define DIO1_IOC_GET_BIT_VALUE	_IOWR(DIO1_IOC_MAGIC, 4, struct bit_info)
#define DIO1_IOC_MAX_NR			4

#endif //_DIO1_H
