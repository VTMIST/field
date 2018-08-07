#ifndef _INCLUDES_H_
#define _INCLUDES_H_

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/io.h>
#include <sys/ioctl.h>
#include <sys/signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/timex.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

//POSIX compliant source
#define FALSE 0
#define TRUE 1
#define false 0
#define true 1
#define False 0
#define True 1
#define null NULL

// typedefs
typedef uint8_t boolean;
typedef uint8_t byte;
typedef uint16_t word;

// macros
// Get the LS byte of a 16 or 32-bit value
#define LS_BYTE(x)  ((byte)(x & 0xFF))

#include "gps_io_thread.h"
   
#endif
