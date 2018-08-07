// Logging module

#ifndef __LOGGING__
#define __LOGGING__
int log_open(const char *dir,
			 const char *file_name,
			 const int max_file_size);
void log_write(const char *str);
void log_close(void);
#endif
