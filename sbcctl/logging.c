/*
	Simple general purpose logging module
*/

#include "includes.h"
#include "logging.h"
#include <semaphore.h>

// Variables
static FILE	*_log_file = NULL;
static int	_max_file_size;
static pthread_mutex_t _mutex = PTHREAD_MUTEX_INITIALIZER;
static char _primary_file_name[255];
static char _secondary_file_name[255];


// Function prototypes
static void log_time_string(char *s);
static off_t fsize(const char *filename);
static void log_limit_file_size(void);


// Open a log file.
// dir example:  		"/var/log"
// file_name example:	"gps_mgr"
// ".log" is appended to file_name.
// Return 1 if successful, 0 if not.
int log_open(const char *dir,
			 const char *file_name,
			 const int max_file_size)
{
	sprintf(_primary_file_name, "%s/%s.log", dir, file_name);
	sprintf(_secondary_file_name, "%s/%s.log.1", dir, file_name);
	_log_file = fopen(_primary_file_name, "at");
	if (_log_file == NULL) {
		printf("\nCould not open log file %s", _primary_file_name);
		return 0;
	}
	_max_file_size = max_file_size;
	return 1;
}


// Prepend date and time to a string
//  and write it to the log file
// Is thread safe.
void log_write(const char *msg)
{
	char time_str[32];
	
	if (_log_file != NULL)
	{
		pthread_mutex_lock(&_mutex);
		log_time_string(time_str);
		fprintf(_log_file, "%s %s\n", time_str, msg);
		fflush(_log_file);
		pthread_mutex_unlock(&_mutex);
		log_limit_file_size();
	}
}


// Limit the size of the log files.
// If the primary log file size has gone over
// the limit, rename it with the secondary log
// file name and open a new primary log file.
static void log_limit_file_size(void)
{
	if (fsize(_primary_file_name) > _max_file_size)
	{	
		pthread_mutex_lock(&_mutex);
		log_close();
		rename(_primary_file_name, _secondary_file_name);
		_log_file = fopen(_primary_file_name, "at");
		if (_log_file == NULL) {
			printf("\nCould not open log file %s", _primary_file_name);
		}
		pthread_mutex_unlock(&_mutex);
	}
}


// Return size of filename
// Return -1 if error.
static off_t fsize(const char *filename)
{
    struct stat st; 

    if (stat(filename, &st) == 0)
        return st.st_size;

    return -1; 
}


void log_close(void)
{
	if (_log_file != NULL) {
		fclose(_log_file);
		_log_file = NULL;
	}
}


// Return the current PC system time
//	in *s in string format:
//	YYYY/MM/DD HH:MM:SS
static void log_time_string(char *s)
{
    time_t			long_time;
	struct tm		*tm_p;

	time(&long_time);				// Get time as long integer
	tm_p = localtime(&long_time);	// Convert to local time
	sprintf(s, "%04d/%02d/%02d %02d:%02d:%02d",
			tm_p->tm_year + 1900,
			tm_p->tm_mon + 1,
			tm_p->tm_mday,
			tm_p->tm_hour,
			tm_p->tm_min,
			tm_p->tm_sec);
}


/*
// Prepend date and time to str and
//	write it to the console log file.
// If there is not console write also write
//  to stdout
static void log_con_msg (char *str)
{
	static BOOL		first_time = TRUE;
	size_t			str_length;
	char			time_str[40];
	char			msg[256];

	if (first_time) {	// open the console log file
		first_time = FALSE;
		console_log_file = fopen(CON_LOG_FILENAME, "at");
		if (console_log_file == NULL) {
			printf("\nCould not open mag_cntl log file.  Disk full?");
		}
	}
	if (console_log_file != NULL) {
		if (*str == '\n') {
			str++;	// skip leading newline (date has newline prepended)
		}
		get_cur_time_string(time_str);
		sprintf(msg, "\n%s %s", time_str, str);	// prepend the current date, time
		str_length = strlen(msg);
		if (fwrite(msg, sizeof(char), str_length, console_log_file) != str_length) {
			printf("\nLog file write failed.  Disk full?");
			close_log_file();
		}
		fflush(console_log_file);
		if (console_redirected()) {
			printf(msg);
			fflush(stdout);
		}
	}
}
*/
