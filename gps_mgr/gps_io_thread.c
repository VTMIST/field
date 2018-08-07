// GPS I/O Thread Wrapper

#include "includes.h"
#include "gps_pps.h"
#include "logging.h"


// Constants
#define CR 0x0D
#define LF 0x0A

// Seconds between UTC syncs
#define DEF_UTC_SYNC_PERIOD (60 * 60)

#define DRIFT_MEAS_PERIOD 30

// typedefs
#define MAX_NUM_NMEA_FIELDS 20
#define MAX_NMEA_FIELD_SIZE 20
typedef char nmea_field_type[MAX_NMEA_FIELD_SIZE];
typedef nmea_field_type nmea_fields_type[MAX_NUM_NMEA_FIELDS];

// Global Vars
static boolean _thread_running = False;
static boolean _stop_thread = False;
static pthread_t _gps_io_thread;
static int _pps_drvr_fd = -1;
static char _log_msg[1024];

static double DRIFT_VAR_LIMIT = 0.000020;
#define DRIFT_FILTER_SIZE 5
static double _drift_filter[DRIFT_FILTER_SIZE];
static int _drift_filter_index = 0;
static int _drift_filter_cnt = 0;

static double ERROR_VAR_LIMIT = 0.005000;
#define ERROR_FILTER_SIZE 5
static double _error_filter[ERROR_FILTER_SIZE];
static int _error_filter_index = 0;
static int _error_filter_cnt = 0;

static struct drift_params{
	boolean measuring;
	struct timeval start_time;
	struct timeval stop_time;
	double rate;
	boolean rate_valid;
	boolean lost_pos_fix;
} _drift_params;

static struct {
	double 	error_secs;
	boolean measure;
} _sys_time_error;

// System clock compensation structure
static struct clock_comp {
	double  drift_rate;			// current sys time drift rate, secs/sec
	double	error;				// current sys time error, secs
	double  drift_comp_rate;	// comp rate required to correct drift
	double  error_comp_rate;	// comp rate required to correct error
								//   during the next sync period
	int		sync_period; 		// seconds until next UTC sync
} _clock_comp;


static time_t  _time_of_last_pos_fix = 0;
static time_t  _time_of_last_sync = 0;
static char	   _latitude[32];
static char	   _longitude[32];
static boolean _receiver_power_on = false;
static boolean _serial_data_received = false;
static boolean _have_pos_fix = false;
static boolean _sys_time_set = false;
static boolean _set_sys_time = false;

static int _serial_port_fd = 0;
static struct termios _old_tio;
#define RX_BYTE_BUF_SIZE 100000
static char _rx_byte_buf[RX_BYTE_BUF_SIZE];

#define RX_BYTE_Q_SIZE 100000
static char _rx_byte_q[RX_BYTE_Q_SIZE];
static int _rx_byte_q_wrt = 0;
static int _rx_byte_q_read = 0;
static int _rx_byte_q_cnt = 0;

#define RX_STR_MAX_SIZE 128
typedef char max_size_gps_str[RX_STR_MAX_SIZE];
#define RX_STR_Q_SIZE 200
static max_size_gps_str _rx_str_q[RX_STR_Q_SIZE];
static int _rx_str_q_wrt = 0;
static int _rx_str_q_read = 0;
static int _rx_str_q_cnt = 0;
static int _rx_str_byte_index = 0;


// Function Prototypes
static void *gps_io_thread_func(void *ptr);
static void close_serial_port(void);
static boolean open_serial_port(void);
static int open_port(void);
static void HandleSerialInput(void);
static void EnqueueRxBytes(char *buf, int len);
static void FlushRxByteQueue(void);
static void EnqueueRxStrs(void);
static void EnqueueRxStr(char *s, int len);
static int DequeueRxBytes(char *buf, int len);
static void FlushRxStrQueue(void);
static void HandleRxStrs(void);
static void ParseNmeaSentence(char *sen, nmea_fields_type fields);
static int GetNextNmeaField(char *s, int s_index, char *field);
static char *GetNextRxStr(void);
static void DequeueRxStr(void);
static int read_serial_bytes(int serial_port_fd,
								char *buf,
								int buf_size);
static boolean send_init_str(char *buf, int buf_len);
static void HandleGprmcSen(nmea_fields_type f);
static uint32_t ConvertToSecs(const char *d, const char *t);
//static int gps_sentence_bytes_received(void);
static void close_pps_drvr(void);
static boolean open_pps_drvr(void);
static boolean init_gps_io_thread(void);
//static void print_pos_fix_status(void);
static void do_gps_tasks(void);

static void start_drift_meas(struct drift_params *p);
static void monitor_drift_meas(struct drift_params *p);
static void stop_drift_meas(struct drift_params *p);
static boolean get_drift_rate(struct drift_params *p, double *drift_rate);
static void get_avg_drift_rate(double *drift_rate);
static double elapsed_secs(struct timeval x,
							struct timeval y);
static boolean calc_drift_rate(const struct drift_measurement *meas,
								double *drift_rate);
static void start_error_meas(void);
static boolean get_sys_time_error(double *error_secs);
static void get_avg_sys_time_error(double *error_secs);
//static void get_and_print_timex(void);
//static void print_timex(const struct timex *status);
static boolean get_timex(struct timex *status);
static boolean set_timex(long tick, long freq);
static void init_clock_comp(struct clock_comp *p);
static void update_comp_rate(struct clock_comp *p);
static void comp_rate_to_freq_tick(double comp_rate,
									long *freq,
									long *tick);
static void set_comp_rate(const long freq,
						const long tick);
static void state_machine(void);
static void set_sys_time(const char *date_str,
						const char *time_str);
static void monitor_fix_status(void);
static void start_pseudo_pps(void);
static void monitor_power_status(void);
static void update_gps_pps_status(void);
static boolean passes_drift_filter(double drift);
static void init_drift_filter(void);
static boolean passes_error_filter(double error);
static void init_error_filter(void);
				

// Start the GPS receiver I/O thread
boolean start_gps_io_thread(void)
{
    int  		ret;
    const int	timeout_period = 5;
    time_t		timeout_time;
   	
    ret = pthread_create(&_gps_io_thread,
                            NULL,
                            gps_io_thread_func,
                            NULL);
    if (ret != 0)
    {
        log_write("start_gps_io_thread: Could not create the GPS I/O thread");
        return False;
    }
    timeout_time = time(NULL) + timeout_period;
	while (!_thread_running)
    {
    	if (time(NULL) > timeout_time)
    	{
    		return false;
    	}
    	usleep(1000000/100);
    }
    return True;
}


// Start the GPS receiver I/O thread
void stop_gps_io_thread(void)
{
	_stop_thread = True;
	while (_thread_running)
		usleep(1000000/20);
}


// GPS receiver I/O thread
static void *gps_io_thread_func(void *ptr)
{    
	_thread_running = True;
	if (!init_gps_io_thread())
	{
		_stop_thread = True;
	}
    while (!_stop_thread)
    {    
    	do_gps_tasks();
        usleep(9 * 1000);   // 9 msec
    }
    //log_write("gps_io_thread_func thread exiting");
    close_serial_port();
    close_pps_drvr();
	system("remove_gps_pps");
    _thread_running = False;
    return null;
}


// Do the miscellaneous thread background tasks.
// This function is called at 50 or 100 Hz.
static void do_gps_tasks(void)
{
	HandleSerialInput();
	monitor_fix_status();
	monitor_power_status();
	state_machine();	
}


// State machine that:
//	- Inits the GPS receiver
//  - Sets system time
//  - Sets hardware clock
//  - Periodically syncs system time with UTC
static void state_machine(void)
{
	enum
	{
		WAIT_FOR_POWER_ON,
		INIT_1,
		INIT_2,
		INIT_3,
		WAIT_FOR_FIRST_FIX,
		SETTLE_1,
		SET_SYSTEM_TIME,
		SETTLE_2,
		MEASURE_DRIFT,
		MEASURE_ERROR,
		WAIT_FOR_NEXT_SYNC
	};
	// Disable all output sentences
	char *cmd_1 = "$PGRMO,,2\x0D,\x0A";
	// Set misc parameters
	char *cmd_2 = "$PGRMC,A,,,,,,,,A,3,,2,4,\x0D,\x0A";		
	// Set misc parameters
	char *cmd_3 = "$PGRMC1,1,1,,,,,1,A,N,,,,2,\x0D,\x0A";		
	// Enable GPRMC sentence
	char *cmd_4 = "$PGRMO,GPRMC,1\x0D,\x0A";

	static int phase = WAIT_FOR_POWER_ON;
	static time_t stop_time;
	static time_t now;
	static boolean pseudo_pps_running = false;
	static boolean system_time_set = false;
	static boolean prev_receiver_power_on = false;

	now = time(NULL);
	if (!_receiver_power_on)
	{
		phase = WAIT_FOR_POWER_ON;
	}
	if (prev_receiver_power_on != _receiver_power_on)
	{
		prev_receiver_power_on = _receiver_power_on;
		if (_receiver_power_on) {
			//log_write("receiver power is on");
		} else {
			//log_write("receiver power is off");
		}
	}
	switch (phase)
	{
		case WAIT_FOR_POWER_ON:
			if (_receiver_power_on)
			{
				//log_write("state_machine: entering INIT_1");
				FlushRxByteQueue();
				FlushRxStrQueue();
				//log_write("starting to initialize GPS receiver");
				send_init_str(cmd_1, strlen(cmd_1));
				stop_time = now + 2;
				//log_write("state_machine: entering INIT_1");
				phase = INIT_1;
				_have_pos_fix = false;
			}
			break;
		case INIT_1:
			if (now > stop_time)
			{
				send_init_str(cmd_2, strlen(cmd_2));
				stop_time = now + 2;
				//log_write("state_machine: entering INIT_2");
				phase = INIT_2;
			}
			break;
		case INIT_2:
			if (now > stop_time) {
				send_init_str(cmd_3, strlen(cmd_3));
				stop_time = now + 2;
				log_write("state_machine: entering INIT_3");
				phase = INIT_3;
			}
			break;
		case INIT_3:
			if (now > stop_time) {
				send_init_str(cmd_4, strlen(cmd_4));
				stop_time = now + 2;
				//log_write("state_machine: entering WAIT_FOR_FIRST_FIX");
				phase = WAIT_FOR_FIRST_FIX;
			}
			break;
	    case WAIT_FOR_FIRST_FIX:
    	    if (now > stop_time) {
    			if (_have_pos_fix)
    			{
    				// Long delay after first fix because it takes a while
    				//  for the latency between PPS and the
    				//  GPRMC sentence to settle to around 600 msec.
    				stop_time = now + 60;
    				phase = SETTLE_1;
    			}
    	    }
			break;			
		case SETTLE_1:
			if (now > stop_time)
			{
				//log_write("finished initializing GPS receiver");
				if (!system_time_set)
				{
					// The state machine sets the system
					//  time from GPS one time only
					// Thereafter only clock rate adjustments
					//  are made.
					system_time_set = true;
					_sys_time_set = false;
					_set_sys_time = true;
					//log_write("state_machine: entering SET_SYSTEM_TIME");
					phase = SET_SYSTEM_TIME;
				}
				else
				{
   				    stop_time = now + DRIFT_MEAS_PERIOD;
    				stop_drift_meas(&_drift_params);
    				start_drift_meas(&_drift_params);
    				init_drift_filter();
    				//log_write("state_machine: entering MEASURE_DRIFT");
    				phase = MEASURE_DRIFT;
				}
			}
			break;
		case SET_SYSTEM_TIME:
		    // Wait here until system time is set from GPS
			if (_sys_time_set)
			{
				stop_time = now + 5;
				//log_write("state_machine: entering SETTLE_2");
				phase = SETTLE_2;
			}
			break;
		case SETTLE_2:
			// Allow time for gps_pps driver to set system time
			if (now > stop_time)
			{
    			//log_write("state_machine: entering SETTLE_2");
				//log_write("system time set from GPS receiver");			
				stop_time = now + DRIFT_MEAS_PERIOD;
				stop_drift_meas(&_drift_params);
				start_drift_meas(&_drift_params);
    			init_drift_filter();
				//log_write("state_machine: entering MEASURE_DRIFT");
				phase = MEASURE_DRIFT;
			}
			break;
		case MEASURE_DRIFT:
			monitor_drift_meas(&_drift_params);
			if (now > stop_time)
			{
				stop_drift_meas(&_drift_params);
				boolean ok;
				ok = (get_drift_rate(&_drift_params, &(_clock_comp.drift_rate))
				            && passes_drift_filter(_clock_comp.drift_rate));
	            if (ok)
	            {
	                get_avg_drift_rate(&(_clock_comp.drift_rate));
    				//double hourly_drift_rate = 3600.0 * _clock_comp.drift_rate * 1000.0;
    				//sprintf(_log_msg, "Drift rate is %f s/s (%f msec/hr)",
    				//		_clock_comp.drift_rate, hourly_drift_rate);
    				//log_write(_log_msg);
    				start_error_meas();
    				//log_write("measured system time drift rate");			
    				//log_write("state_machine: entering MEASURE_ERROR");
    				init_error_filter();
    				phase = MEASURE_ERROR;
	            }
	            else
	            {
    				stop_time = now + DRIFT_MEAS_PERIOD;
    				start_drift_meas(&_drift_params);
    				//log_write("state_machine: entering MEASURE_DRIFT");
	            }
			}
			break;
		case MEASURE_ERROR:		
			// Wait until the error measurement is available
			//  and then set the sys clock comp rate
			if (get_sys_time_error(&(_clock_comp.error)))
			{			    
	            if (!passes_error_filter(_clock_comp.error))
	            {
	                start_error_meas();
                    break;
			    }
			    get_avg_sys_time_error(&(_clock_comp.error));
				//log_write("measured system time error");			
				//sprintf(_log_msg, "System time error is %f secs", _clock_comp.error);
				//log_write(_log_msg);
				update_comp_rate(&_clock_comp);
				double total_comp_rate = _clock_comp.drift_comp_rate +
										_clock_comp.error_comp_rate;
				long tick;
				long freq;
				comp_rate_to_freq_tick(total_comp_rate,
										&freq,
										&tick);
				set_comp_rate(freq, tick);
				if (!pseudo_pps_running)
				{
					start_pseudo_pps();
					pseudo_pps_running = true;
				}
				
				//log_write("system time drift and error compensation updated");
				system("hwclock --systohc");
				//log_write("hardware clock set from system time");
				stop_time = now + _clock_comp.sync_period;
				_time_of_last_sync = now;
				update_gps_pps_status();
				//log_write("state_machine: entering WAIT_FOR_NEXT_SYNC");
				phase = WAIT_FOR_NEXT_SYNC;
			}
			break;
		case WAIT_FOR_NEXT_SYNC:
			// Wait until it's time to sync the clock again
			if (now > stop_time)
			{
				//log_write("state_machine: entering WAIT_FOR_FIRST_FIX");
				phase = WAIT_FOR_FIRST_FIX;	
			}
			break;
		default:
			log_write("state_machine: invalid state");
			//log_write("state_machine: entering WAIT_FOR_POWER_ON");
			phase = WAIT_FOR_POWER_ON;
			break;
	}
}


// Initialize the gps_io_thread
// Return True if successful
static boolean init_gps_io_thread(void)
{
    //log_write("Initializing gps_io_thread");
	system("/aal-pip/field/bin/install_gps_pps");
    if (!open_pps_drvr())
    {
		system("/aal-pip/field/bin/remove_gps_pps");
    	return False;
    }
    open_serial_port();
	init_clock_comp(&_clock_comp);
	strcpy(_latitude, "0.0");
	strcpy(_longitude, "0.0");
	return True;
}


// Move bytes from the driver buffer
//  to a local rx byte queue.
// Handle the received GPS sentences.
void HandleSerialInput(void)
{
    int bytes_read;
    
    bytes_read = read_serial_bytes(_serial_port_fd,
									_rx_byte_buf,
									RX_BYTE_BUF_SIZE-1);
    if (bytes_read > 0)
    {
    	//log_write("HandleSerialInput: got serial data");
    	_serial_data_received = true;
        _rx_byte_buf[bytes_read] = 0;	// terminate string
        EnqueueRxBytes(_rx_byte_buf, bytes_read);
    	EnqueueRxStrs();
    	HandleRxStrs();
    }
}


// Open the serial port if it is not
//  already open.
// Return true if serial port was opened
static boolean open_serial_port(void)
{
    if (_serial_port_fd <= 0)
    {
        _serial_port_fd = open_port();
        if (_serial_port_fd < 0)
        {
            return false;
        }
    }
    //log_write("GPS serial port opened");
    return true;
}


// Open the serial port
// Return the file descriptor
// Return -1 if error
static int open_port(void)
{
    int fd;
	struct termios newtio;
    const char *dev_name = "/dev/ttyS0";
	
    // Open the serial port
	fd = open(dev_name, O_RDWR | O_NOCTTY);
	if (fd < 0)
	{
        perror("open_port: Could not open the GPS serial port ");
        return fd;
	}
	tcgetattr(fd, &_old_tio); // save current port settings 

    // Set up serial port params
	fcntl(fd, F_SETFL, FNDELAY); // prevent read() from blocking
	
	// set new port settings for canonical input processing 
	cfsetispeed(&newtio, B4800);
	cfsetospeed(&newtio, B4800);
	
	newtio.c_cflag |= (CLOCAL | CREAD);
	newtio.c_cflag &= ~CRTSCTS;
	newtio.c_cflag &= ~PARENB;
	newtio.c_cflag &= ~CSTOPB;
	newtio.c_cflag &= ~CSIZE; /* Mask the character size bits */
	newtio.c_cflag |= CS8;    /* Select 8 data bits */
	
	newtio.c_lflag = 0;
	newtio.c_iflag = IGNBRK;
	newtio.c_oflag = 0;
	
	//newtio.c_cc[VMIN] = 47;  // ignored when FNDELAY option selected
	//newtio.c_cc[VTIME] = 20;
	
	tcflush(fd, TCIOFLUSH);
	tcsetattr(fd, TCSANOW, &newtio);
	tcflush(fd, TCIOFLUSH);
	return fd;
}



static void close_serial_port(void)
{
    if (_serial_port_fd > 0)
    {
		tcsetattr(_serial_port_fd, TCSANOW, &_old_tio);
    	fcntl(_serial_port_fd, F_SETFL, FNDELAY);
        close(_serial_port_fd);
        _serial_port_fd = 0;
        //log_write("GPS serial port closed");
    }
}


// Enqueue bytes in the rx byte queue
static void EnqueueRxBytes(char *buf, int len)
{
    if (len < 0) {return;}
    if (len > (RX_BYTE_Q_SIZE - _rx_byte_q_cnt))
    {
        log_write("EnqueueRxBytes: GPS serial rx byte queue overflowed");
        FlushRxByteQueue();
        return;
    }
    _rx_byte_q_cnt += len;
    while (len--)
    {
        _rx_byte_q[_rx_byte_q_wrt++] = *buf++;
        if (_rx_byte_q_wrt >= RX_BYTE_Q_SIZE)
        {
            _rx_byte_q_wrt = 0;
        }
    }
}

static void FlushRxByteQueue(void)
{
    _rx_byte_q_wrt = 0;
    _rx_byte_q_read = 0;
    _rx_byte_q_cnt = 0;
}

// While there are any bytes in the rx byte queue,
// assemble strings (sentences) from the
// rx byte queue.
// Store GPS sentences in the rx string queue.
static void EnqueueRxStrs(void)
{
    char rx_byte;
    static char s[RX_STR_MAX_SIZE];
    
    while (_rx_byte_q_cnt > 0)
    {
        if (_rx_str_byte_index >= (RX_STR_MAX_SIZE - 2))
        {
            // Invalid GPS strings are hard to avoid on
            //  startup and don't cause problems, so don't annoy the user
            log_write("EnqueueRxStrs: invalid GPS string received");
            _rx_str_byte_index = 0;
            continue;
        }
        DequeueRxBytes(&rx_byte, 1);
        s[_rx_str_byte_index++] = rx_byte;
        if (rx_byte == LF)
        {
            if (s[0] != '$')
            {
                // invalid GPS strings are hard to avoid on
                //  startup and don't cause problems, so don't annoy the user
                log_write("EnqueueRxStrs: invalid GPS string received");
                _rx_str_byte_index = 0;
                continue;
            }
            s[_rx_str_byte_index++] = 0;   // terminate string
            EnqueueRxStr(s, _rx_str_byte_index);
            _rx_str_byte_index = 0;
            //log_write("EnqueueRxStrs: Enqueued a GPS rx string");           
        }
    }
}

// Return the number if bytes that EnqueueRxStrs
//  has accumulated in its partial string buffer
//static int gps_sentence_bytes_received(void)
//{
//	return _rx_str_byte_index;
//}


// Dequeue len bytes from rx byte queue
// Return the actual number of bytes dequeued
static int DequeueRxBytes(char *buf, int len)
{
    int dq_cnt = 0;
    
    if (len < 0) {return 0;}   
    while ((len--) && (_rx_byte_q_cnt > 0))
    {
        *buf++ = _rx_byte_q[_rx_byte_q_read++];
        ++dq_cnt;        
        if (_rx_byte_q_read >= RX_BYTE_Q_SIZE)
        {
            _rx_byte_q_read = 0;
        }
        --_rx_byte_q_cnt;
    }
    return dq_cnt;
}

// Enqueue a single string
static void EnqueueRxStr(char *s, int len)
{          
    if (_rx_str_q_cnt >= RX_STR_Q_SIZE)
    {
        log_write("EnqueueRxStr: GPS rx string queue overflowed");
        FlushRxStrQueue();
        return;
    }
    memcpy(&(_rx_str_q[_rx_str_q_wrt]), s, len);
    ++_rx_str_q_cnt;
    if (++_rx_str_q_wrt >= RX_STR_Q_SIZE)
    {
        _rx_str_q_wrt = 0;
    }            
}


static void FlushRxStrQueue(void)
{
    _rx_str_q_wrt = 0;
    _rx_str_q_read = 0;
    _rx_str_q_cnt = 0;
    _rx_str_byte_index = 0;
}


// Separate the comma-separated fields in sen
//  into separate strings in fields
static void ParseNmeaSentence(char *sen, nmea_fields_type fields)
{
    int i;
    int sen_index = 0;
    int field_index = 0;
    nmea_field_type field;
    
    for (i = 0; i < MAX_NUM_NMEA_FIELDS; ++i)
    {
        fields[i][0] = 0;   // terminate all the field strings
    }    
    while (true)
    {
        sen_index = GetNextNmeaField(sen, sen_index, field);
        if (sen_index < 0)
        {
            break; // end of the sentence
        }
        strcpy(fields[field_index++], field);
        if (field_index >= MAX_NUM_NMEA_FIELDS)
        {
            break;
        }       
    }
}

// Get the next field string from an NMEA sentence
// Return the updated s_index
// Return -1 if end of sentence (no field returned)
static int GetNextNmeaField(char *s, int s_index, char *field)
{
    int i = 0;
    char ch;
    
    while (true)
    {
        field[i] = 0;
        if (i >= MAX_NMEA_FIELD_SIZE - 1) {return -1;}
        ch = s[s_index++];
        if (ch == CR) {return -1;}
        if (ch == ',') {return s_index;}
        field[i++] = ch;
    }
}

// Return a ptr to the string at
// the front of the queue
static char *GetNextRxStr(void)
{
    if (_rx_str_q_cnt <= 0)
    {
        return null;
    }
    return _rx_str_q[_rx_str_q_read];
}

// Dequeue (destroy) the string at
//  the front of the queue
static void DequeueRxStr(void)
{
    if (_rx_str_q_cnt <= 0)
    {
        return;
    }
    if (++_rx_str_q_read >= RX_STR_Q_SIZE)
    {
        _rx_str_q_read = 0;
    }
    --_rx_str_q_cnt;
}


// Read and return all the rx bytes currently
//  available in a serial port rx buffer.
// If buf is not big enough, fill buf and
//  leave the remaining rx bytes in the
//  serial port buffer.
static int read_serial_bytes(int serial_port_fd,
								char *buf,
								int buf_size)
{
    int bytes_avail;
    ioctl(serial_port_fd, FIONREAD, &bytes_avail);
    if (bytes_avail == 0)
    {
    	return 0;
    }
	if (bytes_avail > buf_size)
    {
        read(serial_port_fd, buf, buf_size);
        return buf_size;
    }
    read(serial_port_fd, buf, bytes_avail);
    return bytes_avail;
}


// Send an initialization string to the
//  GPS receiver.
// Return True if successful.
static boolean send_init_str(char *buf, int buf_len)
{
	int bytes_sent;
	
	bytes_sent = write(_serial_port_fd, buf, buf_len);
	if (bytes_sent != buf_len)
	{
		log_write("send_init_str: Error transmitting command sentence to GPS receiver");
		return False;
	}
	return True;
}

// Process a complete enqueued GPS sentence
static void HandleRxStrs(void)
{
    enum {
        WAITING_FOR_GPRMC,
        WAITING_FOR_GPGGA
    };
    char *str;
    nmea_fields_type fields;
    
    while (true)
    {
        str = GetNextRxStr();
        if (str == null) {return;}
        ParseNmeaSentence(str, fields);
		if (strcmp(fields[0], "$GPRMC") == 0)
        {
        	//sprintf(_log_msg, "HandleRxStrs: got %s", str);
        	//log_write(_log_msg);
            HandleGprmcSen(fields);
            //log_write("HandleRxStrs: Processing $GPRMC GPS sentence");
            //log_write(str);
        }
        else
        {
        	//sprintf(_log_msg, "HandleRxStrs: got %s", str);
        	//log_write(str);
        }
        DequeueRxStr();
    }
}


// Handle an NMEA $GPRMC sentence
static void HandleGprmcSen(nmea_fields_type f)
{
/*
$GPRMC,135251,V,4217.6331,N,08342.6643,W,,,180510,006.6,W*60
$GPRMC,134724,A,4217.6448,N,08342.6906,W,001.0,231.8,180510,006.6,W*7F
*/
    const int UTC_TIME = 1;
    const int STATUS = 2;
    const int LAT = 3;
    const int LAT_N_S = 4;
    const int LONG = 5;
    const int LONG_E_W = 6;   
    const int UTC_DATE = 9;

	//log_write("HandleGprmcSen: got $GPRMC sentence");
	_have_pos_fix = (f[STATUS][0] == 'A');
	if (!_have_pos_fix)
	{
		//log_write("HandleGprmcSen: no GPS position fix");
		return;
	}
	//log_write("HandleGprmcSen: have position fix");
	_time_of_last_pos_fix = time(NULL);
	set_sys_time(f[UTC_DATE], f[UTC_TIME]);
    if (_sys_time_error.measure)
    {
    	struct timeval sys_time;
	    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_GET_TIME, &sys_time) < 0)
		{
			log_write("HandleGprmcSen: ioctl GPS_PPS_IOC_GET_TIME failed");
		}
		struct timeval utc_time;
		utc_time.tv_sec = ConvertToSecs(f[UTC_DATE], f[UTC_TIME]);
		utc_time.tv_usec = 0;
		_sys_time_error.error_secs = elapsed_secs(utc_time, sys_time);
    	_sys_time_error.measure = false;
    }
    if (f[LAT_N_S][0] == 'S')
    {
    	sprintf(_latitude, "%s%s", "-", f[LAT]);
    }
    else
    {
    	strcpy(_latitude, f[LAT]);
    }
    if (f[LONG_E_W][0] == 'W')
    {
    	sprintf(_longitude, "%s%s", "-", f[LONG]);
    }
    else
    {
    	strcpy(_longitude, f[LONG]);
    }   
	struct timeval sys_time;
	gettimeofday(&sys_time, NULL);
	//sprintf(_log_msg, "System Time =            %d s, %d usec", (int)sys_time.tv_sec, (int)sys_time.tv_usec);
	//log_write(_log_msg);					
	//log_write("HandleGprmcSen: GPS receiver has position fix");
	//uint32_t utc_secs_since_1970 = ConvertToSecs(f[UTC_DATE], f[UTC_TIME]);
	//sprintf(_log_msg, "Time from GPS receiver = %d s", utc_secs_since_1970);
	//log_write(_log_msg);
}


// Set the Linux system time acurately using the gps_pps
//  driver if the _set_sys_time flag is set.
// date_str and time_str are fields from the $GPRMC sentence.
static void set_sys_time(const char *date_str,
					const char *time_str)
{
	if (!_set_sys_time)
	{
		return;
	}
    // The gps_pps driver will set the sys time
    //  when the next PPS interrupt occurs.
    // As measured on a scope, the last byte of the $GPRMC
    //  sentence arrives around 670 msec after the time it
    //  reports (the time of previous PPS).
    // The time of arrival of the last byte of $GPRMC
    //  may be as much as 800 msec after PPS.
    // That gives us around 200-300 msec to tell the driver
    //  to set the system time when the next PPS interrupt
    //  occurs.
    struct timeval next_sec;
	next_sec.tv_sec = ConvertToSecs(date_str, time_str) + 1;
	next_sec.tv_usec = 0;
    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_SET_TIME, &next_sec) < 0)
	{
		log_write("set_sys_time: ioctl GPS_PPS_IOC_SET_TIME failed");
	}
	_set_sys_time = false;
    _sys_time_set = true;
    //log_write("System time set to UTC");
}



// Convert the UTC time and date strings from the
//  $GPRMC sentence to a number of seconds
//  since the start of 1970
static uint32_t ConvertToSecs(const char *d, const char *t)
{
	struct tm tm_struct;
    char s[8];
    int year, month, dom, hours, minutes, seconds;
    
    if ((strlen(d) < 6) || (strlen(t) < 6)) {return 0;}
    
    s[0] = d[0]; s[1] = d[1]; s[2] = 0;
    dom = atoi(s);
    s[0] = d[2]; s[1] = d[3];
    month = atoi(s);
    s[0] = d[4]; s[1] = d[5];
    year = atoi(s);

    s[0] = t[0]; s[1] = t[1];
    hours = atoi(s);
    s[0] = t[2]; s[1] = t[3];
    minutes = atoi(s);
    s[0] = t[4]; s[1] = t[5];
    seconds = atoi(s);
    
	tm_struct.tm_year = (2000 + year) - 1900;
	tm_struct.tm_mon = month - 1;
	tm_struct.tm_mday = dom;
	tm_struct.tm_hour = hours;
	tm_struct.tm_min = minutes;
	tm_struct.tm_sec = seconds;
	tm_struct.tm_isdst = 0;
	
	return (int)mktime(&tm_struct);
}

// Open the GPS PPS (pulse per second) driver
// Store the file descriptor in _pps_drvr_fd
// Return False if error
static boolean open_pps_drvr(void)
{
    int fd;
    const char *dev_name = "/dev/gps_pps";
	
	if (_pps_drvr_fd > 0)
	{
		return True;
	}
	fd = open(dev_name, O_RDWR);
	if (fd < 0)
	{
        perror("open_pps_drvr: Could not open the GPS PPS driver ");
        _pps_drvr_fd = -1;
        return False;
	}
	_pps_drvr_fd = fd;
	return True;
}


// Close the GPS PPS (pulse per second) driver
static void close_pps_drvr(void)
{
    if (_pps_drvr_fd > 0)
    {
        close(_pps_drvr_fd);
        _pps_drvr_fd = -1;
    }
}


// Print the current position fix status
//  if it has changed
/*
static void print_pos_fix_status(void)
{
	static boolean had_pos_fix = true;
	
	if (had_pos_fix != _have_pos_fix)
	{
		if (_have_pos_fix)
		{
			log_write("Acquired GPS position fix");
		}
		else
		{
			log_write("Lost GPS position fix");
		}
		had_pos_fix = _have_pos_fix;
	}
}		
*/

// Start a system clock drift rate measurement
static void start_drift_meas(struct drift_params *p)
{
	//log_write("Starting system clock drift rate measurement");
    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_START_DRIFT, NULL) < 0)
	{
		log_write("start_drift_meas: ioctl GPS_PPS_IOC_START_DRIFT failed");
	}
	p->lost_pos_fix = false;
	p->rate_valid = false;
}


// Stop the system clock drift rate measurement and
//  calculate the drift rate.
static void stop_drift_meas(struct drift_params *p)
{
	struct drift_measurement	meas;
	
	//log_write("Stopping system clock drift measurement");
    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_STOP_DRIFT, NULL) < 0)
	{
		log_write("stop_drift_meas: ioctl GPS_PPS_IOC_STOP_DRIFT failed");
	}
    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_GET_DRIFT, &meas) < 0)
	{
		log_write("stop_drift_meas: ioctl GPS_PPS_IOC_GET_DRIFT failed");
	}
	/*
	sprintf(_log_msg, "  begin_sys_time = %d s, %d usec", meas.begin_sys_time.tv_sec,
							meas.begin_sys_time.tv_usec);
	log_write(_log_msg);
	sprintf(_log_msg, "  end_sys_time = %d s, %d usec", meas.end_sys_time.tv_sec,
							meas.end_sys_time.tv_usec);
	log_write(_log_msg);
	sprintf(_log_msg, "  gps_seconds = %d", meas.gps_seconds);
	log_write(_log_msg);
	*/
   	boolean valid = calc_drift_rate(&meas, &(p->rate));
   	p->rate_valid =  valid && (!(p->lost_pos_fix));
    //sprintf(_log_msg, "Drift rate is %f secs/sec", p->rate);
    //log_write(_log_msg);	    
}

// Called periodically during drift rate measurements
//  to record the loss of GPS position fix
static void monitor_drift_meas(struct drift_params *p)
{
	if (!_have_pos_fix)
	{
		p->lost_pos_fix = true;
	}
}


// Return the most recently measured
// system clock drift rate in secs/sec.
// Return true if the drift rate is valid.
static boolean get_drift_rate(struct drift_params *p,
							  double *drift_rate)
{
	if (!(p->rate_valid))
	{
		return false;
	}	
	*drift_rate = p->rate;
	return true;
}


// Return the average of the drift rates
//  in _drift_filter.
static void get_avg_drift_rate(double *drift_rate)
{
    double sum = 0.0;
    int i;
    
    for (i = 0; i < DRIFT_FILTER_SIZE; ++i) {
        sum += _drift_filter[i];
    }
	*drift_rate = sum / (double)DRIFT_FILTER_SIZE;
}



// Given a system time drift measurement,
// calculate the rate at which it is drifting
// away from UTC.
// The drift is positive if the system clock
//	is running faster than UTC.
// Return secs per sec of drift in *drift_rate.
// Return false if time measurement is not valid.
static boolean calc_drift_rate(const struct drift_measurement *meas,
						 		double *drift_rate)
{
	double sys_elapsed_secs = elapsed_secs(meas->begin_sys_time,
											meas->end_sys_time);
	double utc_secs = (double)(meas->gps_seconds);
	double drift_secs = sys_elapsed_secs - utc_secs;
	
	if ((sys_elapsed_secs < 1.0) || (utc_secs < 1.0))
	{
		// insufficient measurment time
		return false;
	}	
	if (fabs(drift_secs) > 0.5)
	{
		// Amt of drift during measurement should be small
		return false;
	}
	*drift_rate = drift_secs / utc_secs;
	return true;	
}



// Calculate the elapsed seconds between x and y.
// If x < y the result is positive.
// If x > y the result is negative.
static double elapsed_secs(struct timeval x,
							struct timeval y)
{
	const double million = 1000000.0;
	
	double x_usecs = ((double)x.tv_sec) * million + (double)x.tv_usec;
	double y_usecs = ((double)y.tv_sec) * million + (double)y.tv_usec;
	return (y_usecs - x_usecs) / million;
}


// Start a system time error measurement
static void start_error_meas(void)
{
	_sys_time_error.measure = true;
}


// Return the results of the most recent
//  system time measurement.
// Return true if the measurement is available.
static boolean get_sys_time_error(double *error_secs)
{
	if (_sys_time_error.measure)
	{
		// still measuring
		return false;
	}
    //snprintf(_log_msg, sizeof(_log_msg), "in get_sys_time_error: measured time error is %f s", _sys_time_error.error_secs);
    //log_write(_log_msg);
	*error_secs = _sys_time_error.error_secs;
	return true;
}


// Return the average of the sys time errors
//  in _error_filter.
static void get_avg_sys_time_error(double *error_secs)
{
    double sum = 0.0;
    int i;
    
    for (i = 0; i < ERROR_FILTER_SIZE; ++i) {
        sum += _error_filter[i];
    }
	*error_secs = sum / (double)ERROR_FILTER_SIZE;
}


/*
			// Call adjtimex() to get the system clock parameters
			//  and display them
			static void get_and_print_timex(void)
			{
				struct timex params;
				
				if (!get_timex(&params))
				{
					return;
				}
				print_timex(&params);	
			}
*/


// Use adjtimex() to set the system clock
//  tick and freq values.
// Return true if successful.
static boolean set_timex(long tick, long freq)
{
	struct timex params;
	int ret_val;
	
	if (!get_timex(&params))
	{
		return false;
	}
	params.tick = tick;
	params.freq = freq;
	params.modes = ADJ_FREQUENCY | ADJ_TICK;
	ret_val = adjtimex(&params);
	if (ret_val < 0)
	{
		log_write("set_timex: adjtimex() failed");
		return false;
	}
	return true;	
}



// Call adjtimex() to get the system clock parameters.
// Return true if successful.
static boolean get_timex(struct timex *params)
{
	int ret_val;
	
	params->modes = 0;		// Get status, don't adjust any parameter
	ret_val = adjtimex(params);
	if (ret_val < 0)
	{
		log_write("get_timex: adjtimex() failed");
		return false;
	}
	return true;
}


/*
	// Print all the system clock status values in params
	static void print_timex(const struct timex *params)
	{
		printf("System clock parameters from adjtimex():\n");
		printf("  modes:     %d\n", params->modes);
		printf("  offset:    %ld\n", params->offset);
		printf("  maxerror:  %ld\n", params->maxerror);
		printf("  status:    %d\n", params->status);
		printf("  constant:  %ld\n", params->constant);
		printf("  precision: %ld\n", params->precision);
		printf("  tolerance: %ld\n", params->tolerance);
		printf("  time:      %d s, %d usec\n", (int)params->time.tv_sec, (int)params->time.tv_usec);
		printf("  tick:      %ld\n", params->tick);	
	}
*/


// Initialize a clock_comp structure.
// Set the adjtimex parameters to match
//  the contents of *p.
static void init_clock_comp(struct clock_comp *p)
{
	p->error = 0.0;
	p->drift_rate = 0.0;
	p->error_comp_rate = 0.0;
	p->drift_comp_rate = 0.0;
	p->sync_period = DEF_UTC_SYNC_PERIOD;
	double total_comp_rate = p->drift_comp_rate +
							 p->error_comp_rate;
	long tick, freq;
	comp_rate_to_freq_tick(total_comp_rate,
							&freq,
							&tick);
	set_comp_rate(freq, tick);
}


// Convert a clock compensation rate to
// adjtimex freq and tick.
// comp_rate units are secs/sec.
// See adjtimex() man page for freq and tick.
static void comp_rate_to_freq_tick(double comp_rate,
									long *freq,
									long *tick)
{
	long ppm;
	long sign;
	
	sign = comp_rate >= 0.0 ? 1 : -1;	
	ppm = (long)fabs(comp_rate * 1000000.0);
	
	*tick = 10000L;		// nominal value
	while (ppm > 100)
	{
		*tick += sign;
		ppm -= 100;
	}
	*freq = ppm * 65536L * sign;
}									

// Set the system clock rate compensation
//  to bring it into sync with UTC
static void set_comp_rate(const long freq,
						const long tick)
{
	//sprintf(_log_msg, "set_comp_rate: freq = %ld, tick = %ld", freq, tick);
	//log_write(_log_msg);
	set_timex(tick, freq);
	//sprintf(_log_msg, "set_comp_rate: rate was set");
	//log_write(_log_msg);
}


// Given the data in *p, calculate new clock compensation
//  rates required to counteract the measured systematic clock
//  drift and current time error.
// p->drift_comp_rate and
// p->error_comp_rate are updated.
// Return true if the calculation was successful.
static void update_comp_rate(struct clock_comp *p)
{
	//log_write("update_comp_rate:");
	sprintf(_log_msg, "  sys time error =         %f s", p->error);
	log_write(_log_msg);
	sprintf(_log_msg, "  sys time drift_rate =    %f s/s", p->drift_rate);
	log_write(_log_msg);
	sprintf(_log_msg, "  old drift comp rate =    %f s/s", p->drift_comp_rate);
	log_write(_log_msg);
	sprintf(_log_msg, "  old error comp rate =    %f s/s", p->error_comp_rate);
	log_write(_log_msg);

	// The current measured drift rate is is the sum of:
	//	 1. residual systematic clock drift
	//   2. p->drift_comp_rate applied by the prev sync
	//	 3. p->error_comp_rate applied by the prev sync
	// Calculate how much of the current measured
	//  drift rate is due to residual systematic clock drift.	
	double residual_sys_drift_rate = p->drift_rate - p->error_comp_rate;
	sprintf(_log_msg, "  residual_sys_drift_rate =    %f s/s", residual_sys_drift_rate);
	log_write(_log_msg);
	
	// Update the drift compensation rate
	p->drift_comp_rate -= residual_sys_drift_rate;
	sprintf(_log_msg, "  new drift comp rate =    %f s/s", p->drift_comp_rate);
	log_write(_log_msg);
	
	// Calculate the current time error compensation rate
	//  needed to correct the current time error in time
	//  for the next sync.
	p->error_comp_rate = -(p->error/(double)p->sync_period);
	sprintf(_log_msg, "  new error comp rate =    %f s/s", p->error_comp_rate);
	log_write(_log_msg);	
	sprintf(_log_msg, "  time sync period =       %d s", p->sync_period);
	log_write(_log_msg);
	
}


// Clear the _have_pos_fix flag if
//  a valid position fix has not been
//  received recently.
static void monitor_fix_status(void)
{
	const int threshold = 2;	// seconds until timeout
	
	if (!_have_pos_fix)
	{
		return;
	}
	if (time(NULL) > _time_of_last_pos_fix + threshold)
	{
		_have_pos_fix = false;
	}
}


// Tell the gps_pps driver to start
//  producing pseudo PPS pulses
static void start_pseudo_pps(void)
{
    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_START_PSEUDO_PPS) < 0)
	{
		log_write("start_pseudo_pps: ioctl GPS_PPS_IOC_START_PSEUDO_PPS failed");
	}
}


// Set or clear the _receiver_power_on flag
//  depending on whether or not serial 
//  GPS data has not been recently received.
static void monitor_power_status(void)
{
	static boolean first_time = true;
	static time_t stop_time;
	const int threshold = 5;	// timeout seconds
	
	if (first_time)
	{
		first_time = false;
		stop_time = time(NULL) + threshold;
		return;
	}
	if (_serial_data_received)
	{
		_serial_data_received = false;
		_receiver_power_on = true;
		stop_time = time(NULL) + threshold;
		return;
	}
	if (_receiver_power_on && (time(NULL) > stop_time))
	{
		_receiver_power_on = false;
	}
}


// Send a status information to the gps_pps driver.
// Other processes can read this status information
// from /proc/gps_pps
static void update_gps_pps_status(void)
{
	struct gps_pps_status	stat;
	
	stat.time_of_last_sync = _time_of_last_sync;
	// Note: floating point values are passed in
	//	string form since the kernel sprintf doesn't
	//	support floating point conversion.
	sprintf(stat.error, "%f", _clock_comp.error);
	strcpy(stat.latitude, _latitude);
	strcpy(stat.longitude, _longitude);
	
    if (ioctl(_pps_drvr_fd, GPS_PPS_IOC_SET_PROC_STATUS, &stat) < 0)
	{
		log_write("update_gps_pps_status: ioctl GPS_PPS_IOC_SET_STATUS_STRING failed");
	}
}


// Init the drift measurement filter
static void init_drift_filter(void)
{
    _drift_filter_index = 0;
    _drift_filter_cnt = 0;
}


// Return true if drift passes the drift
//  filter.
// In order to pass the filter, DRIFT_FILTER_SIZE
//  consecutive drift readings must be
//  within DRIFT_VAR_LIMIT s/s of each other.
// This should filter out the occasional
//  bogus reading.
static boolean passes_drift_filter(double drift)
{
    //char msg[128];
    //snprintf(msg, sizeof(msg), "drift_filter: measurement = %f", drift);
    //log_write(msg);
    _drift_filter[_drift_filter_index++] = drift;
    if (_drift_filter_index == DRIFT_FILTER_SIZE) {
        _drift_filter_index = 0;
    }
    if (_drift_filter_cnt < DRIFT_FILTER_SIZE) {
        ++_drift_filter_cnt;
    }
    if (_drift_filter_cnt == DRIFT_FILTER_SIZE)
    {
        int i;
        for (i = 0; i < DRIFT_FILTER_SIZE - 1; ++i) {
             double diff = fabs(_drift_filter[i] - _drift_filter[i + 1]);
            //snprintf(msg, sizeof(msg), "drift_filter: diff = %f", diff);
            //log_write(msg);
            if (diff > DRIFT_VAR_LIMIT) {
                return false;
            }
        }
        return true;
    }
    return false;
}


// Init the error measurement filter
static void init_error_filter(void)
{
    _error_filter_index = 0;
    _error_filter_cnt = 0;
}


// Return true if error passes the error
//  filter.
// In order to pass the filter, ERROR_FILTER_SIZE
//  consecutive error readings must be
//  within ERROR_VAR_LIMIT s/s of each other.
// This should filter out the occasional
//  bogus reading.
static boolean passes_error_filter(double error)
{
    //char msg[128];
    //snprintf(msg, sizeof(msg), "error_filter: measurement = %f", error);
    //log_write(msg);
    _error_filter[_error_filter_index++] = error;
    if (_error_filter_index == ERROR_FILTER_SIZE) {
        _error_filter_index = 0;
    }
    if (_error_filter_cnt < ERROR_FILTER_SIZE) {
        ++_error_filter_cnt;
    }
    if (_error_filter_cnt == ERROR_FILTER_SIZE)
    {
        int i;
        for (i = 0; i < ERROR_FILTER_SIZE - 1; ++i) {
             double diff = fabs(_error_filter[i] - _error_filter[i + 1]);
            //snprintf(msg, sizeof(msg), "error_filter: diff = %f", diff);
            //log_write(msg);
            if (diff > ERROR_VAR_LIMIT) {
                return false;
            }
        }
        return true;
    }
    return false;
}














