
#include "includes.h"
#include "logging.h"


// Global Constants
#define LOG_FILE_DIR 		"/var/log"
#define LOG_FILE_NAME 		"gps_mgr"
#define LOG_FILE_MAX_SIZE 	200000


// Global Vars
static volatile int _exit_flag = False;


// Function Protypes
static boolean start_threads(void);
static void stop_threads(void);
static void set_up_signals(void);
void termination_handler(int signum);


int main(void)
{
	set_up_signals();	// must do before starting threads
	log_open(LOG_FILE_DIR, LOG_FILE_NAME, LOG_FILE_MAX_SIZE);
	log_write("********* gps_mgr started *********");
	if (!start_threads())
	{
		exit(EXIT_FAILURE);
	}
	//log_write("Waiting for a SIGNAL");
	while (!_exit_flag)
	{
		usleep(1000000/2);
	}
	//log_write("Stopping GpsRxThread");
	stop_threads();
	usleep(1 * 1000000);
	log_write("gps_mgr exiting");
	log_close();
	//log_write("Terminating process");
	exit(EXIT_SUCCESS);
}


// Start the child threads
static boolean start_threads(void)
{
	if (!start_gps_io_thread())
	{
        log_write("start_threads: start_gps_io_thread failed");
        return False;
    }
    return True;
}


// Stop the child threads
static void stop_threads(void)
{
	stop_gps_io_thread();
}



/*
	Assign signal handler to the termination
	signals so this process can clean up
	before being terminated remotely
*/
static void set_up_signals(void)
{
    signal(SIGINT, termination_handler);
    signal(SIGQUIT, termination_handler);
}


/*
	Termination handler.
	Invoked when a signal is received.
	Tells the main loop to terminate the process.
*/
void termination_handler(int signum)
{
    switch (signum) {
        case 2:     log_write("Got SIGINT (shutting down)");   break;
        case 3:     log_write("Got SIGQUIT (shutting down)");   break;
        default:    log_write("Got unknown signal (shutting down)");
    }
	_exit_flag = True;
}



