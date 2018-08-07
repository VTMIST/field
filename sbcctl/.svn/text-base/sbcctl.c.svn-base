/*************************************************************************
 *
 *  SBC Control Program
 *
 *  2006-08-20  Todd Valentic
 *              Initial implementation. Version 1.0
 *
 *  2006-09-01  Todd Valentic
 *              Added tempSensor
 *              Set outputs to low in initDIO()
 *              Version 1.1
 *
 *  2007-02-25  Todd Valentic
 *              Bogus temperature readings in cold weather.
 *              Negative numbers not handled correctly - need to mask
 *              off upper bits and use isNegative.
 *              Version 1.2
 *
 *  2007-03-26  Todd Valentic
 *              Added readings from the TS-9700 ADC board.
 *              Version 1.3
 *
 *  2007-08-10  Todd Valentic
 *              Added DIO from header DIO1
 *              Version 1.4
 *
 *  2007-09-10  Todd Valentic
 *              Added control of LEDs
 *              Added marker option (old default action)
 *              Version 1.5
 *
 *  2008-02-20  Todd Valentic
 *              Added serial functions
 *
 *  2008-08-18  Todd Valentic
 *              Add 20usec delay in TS9700 sampling routines.
 *
 *  2009-10-02  Todd Valentic
 *              Removed serial functions (not needed anymore)
 *              Fixed bug in reading temperature that reset DIO1:8
 *
 *  2009-10-18  Todd Valentic
 *              Code cleanup (replace peek/poke functions)
 *              Add power control functions
 *              Include power data in status output
 *              Include metadata in status output
 *              Version 2.0
 *
 *  2009-10-19  Todd Valentic
 *              Add LED state to power section in Status output
 *              Allow lower case "DIO1" in options
 *              Deprecate "setled" - use "led" instead
 *              Version 2.1
 *
 *  2009-11-09  Todd Valentic
 *              Added noadc option for status
 *              Version 2.2.1
 *
 *	2010-07-08  Steve Musko
 *				Now controlling DIO1.0 - DIO1.6 using dio1 driver to
 *				avoid conflict with gps_pps driver which is controlling
 *				DIO1.7 and DIO1.8.
 *
 ************************************************************************/

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <time.h>

#include "board.h"
#include "logging.c"

// Global Constants
#define LOG_FILE_DIR 		"/var/log"
#define LOG_FILE_NAME 		"sbcctl"
#define LOG_FILE_MAX_SIZE 	50000


static const char* VERSION = "2.2.1";

typedef int (Callback)(Board* board, char* option[], int numOpts);

void    PrintUsage();

void    ReadJumpers (Board* board);
void    ReadPins    (Board* board, DIOPort dio);
void    ReadDirs    (Board* board, DIOPort dio);
void    ReadTS9700  (Board* board);
void    ReadEP9301  (Board* board);
void    ReadRouterAnalog  (Board* board);

int     Status              (Board* board, char* option[], int numOpts);
int     SetDirs             (Board* board, char* option[], int numOpts);
int     SetDir              (Board* board, char* option[], int numOpts);
int     SetPins             (Board* board, char* option[], int numOpts);
int     SetPin              (Board* board, char* option[], int numOpts);
int     SetLED              (Board* board, char* option[], int numOpts);
int     SetEthernetPower    (Board* board, char* option[], int numOpts);
int     SetUSBPower         (Board* board, char* option[], int numOpts);
int     SetRS232Power       (Board* board, char* option[], int numOpts);
int     SetPC104Power       (Board* board, char* option[], int numOpts);
int     SetCPUSpeed         (Board* board, char* option[], int numOpts);
int     PrintHelp           (Board* board, char* option[], int numOpts);
int 	file_exists			(const char *filename);


typedef struct {
    char*       name;
    Callback*   callback;
    int         numOptions;
    char*       usage;
    char*       desc;
} CommandEntry;

static const CommandEntry Commands[] = {
{"status",      Status,         0,  "[noadc]","Print DIO and ADC values"  },
{"setdir",      SetDir,         3,  "<dio> <pin> <dir>","Set pin in/out"    },
{"setdirs",     SetDirs,        2,  "<dio> mask","Set dirs (0-in,1-out)"    },
{"setpin",      SetPin,         3,  "<dio> <pin> <state>","Set pin value"   },
{"setpins",     SetPins,        2,  "<dio> mask","Set all pins on port"     },
{"setled",      SetLED,         2,  "<led> <state>","Deprecated - use led"  },
{"led",         SetLED,         2,  "<led> <state>","Set LED state"         },
{"ethernet",    SetEthernetPower,1,  "<state>","Ethernet power"             },
{"usb",         SetUSBPower,     1,  "<state>","USB power"                  },
{"pc104",       SetPC104Power,  1,  "<state>","PC104 5v boost regulator"    },
{"rs232",       SetRS232Power,  1,  "<state>","RS232 level converter power" },
{"cpu",         SetCPUSpeed,    1,  "<speed>","Set CPU speed"               },
{"help",        PrintHelp,      0,  "",         "Display options"           }
};

static const int NumCommands = sizeof(Commands)/sizeof(CommandEntry);

/*------------------------------------------------------------------------*/

int PrintHelp (Board* board, char* option[], int numOpts)
{
    PrintUsage();
    return 1;
}

void LowerCase (char* buffer) {
    for (; *buffer; buffer++) {
        *buffer = tolower(*buffer);
    }
}

int ParseState (char* option)
{
    if (strcmp(option,"on")==0) {
        return 1;
    } else if (strcmp(option,"off")==0) {
        return 0;
    } else if (strcmp(option,"1")==0) {
        return 1;
    } else {
        return 0;
    }
}

int ParseSpeed (char* option)
{
    if (strcmp(option,"max")==0) {
        return CPU_MAX;
    } else if (strcmp(option,"166")==0) {
        return CPU_166;
    } else if (strcmp(option,"42")==0) {
        return CPU_42;
    } else if (strcmp(option,"min")==0) {
        return CPU_MIN;
    } else {
        return -1;
    }
}

int Status (Board* board, char* option[], int numOpts)
{
    struct tm *now;
    time_t curtime;
    char timestamp[80];
    int hasadc=1;

    if (numOpts==2) {
        hasadc = strcmp(option[1],"noadc")!=0;
    }

    curtime = time(NULL);
    now = localtime(&curtime);
    strftime(timestamp,sizeof(timestamp),"%Y-%m-%d %H:%M:%S",now);

    printf("[metadata]\n");
    printf("version: %s\n",VERSION);
    printf("timestamp: %s\n",timestamp);

    printf("[DIO1]\n");
    //log_write("Status: calling ReadDirs(board,DIO1)");
    ReadDirs(board,DIO1);
    //log_write("Status: calling ReadPins(board,DIO1)");
    ReadPins(board,DIO1);

    printf("[DIO2]\n");
    //log_write("Status: calling ReadDirs(board,DIO2)");
    ReadDirs(board,DIO2);
    //log_write("Status: calling ReadPins(board,DIO2)");
    ReadPins(board,DIO2);

    printf("[jumpers]\n");
    //log_write("Status: calling ReadJumpers");
    ReadJumpers(board);

    printf("[temp]\n");
    //log_write("Status: calling board_get_temp");
    printf("temp_c: %f\n",board_get_temp(board));

    //log_write("Status: calling board_init_adc_TS9700");
    if (hasadc && board_init_adc_TS9700(board)) {
        printf("[TS9700]\n");
        //log_write("Status: calling ReadTS9700");
        ReadTS9700(board);
    }

    //log_write("Status: calling board_init_adc_EP9301");
    if (hasadc && board_init_adc_EP9301(board)) {
        printf("[EP9301]\n");
        //log_write("Status: calling ReadEP9301");
        ReadEP9301(board);
        printf("[router]\n");
        //log_write("Status: calling ReadRouterAnalog");
        ReadRouterAnalog(board);
    }
    printf("[power]\n");
    //log_write("Status: calling board_get_ethernet_power");
    printf("ethernet: %d\n",board_get_ethernet_power(board));
    //log_write("Status: calling board_get_usb_power");
    printf("usb: %d\n",board_get_usb_power(board));
    //log_write("Status: calling board_get_pc104_power");
    printf("pc104: %d\n",board_get_pc104_power(board));
    //log_write("Status: calling board_get_rs232_power");
    printf("rs232: %d\n",board_get_rs232_power(board));
    //log_write("Status: calling board_get_led(board,RED)");
    printf("led.red: %d\n",board_get_led(board,RED));
    //log_write("Status: calling board_get_ethernet_power(board,GREEN)");
    printf("led.green: %d\n",board_get_led(board,GREEN));

    printf("cpu: ");
    //log_write("Status: calling board_get_cpu_speed");
    switch (board_get_cpu_speed(board)) {
        case CPU_MAX:   printf("max\n");     break;
        case CPU_166:   printf("166\n");     break;
        case CPU_42:    printf("42\n");      break;
        case CPU_MIN:   printf("min\n");     break;
        default:        printf("unknown\n"); break;
    }
    return 1;
}

void ReadPins (Board* board, DIOPort dio)
{
    int state   = board_get_pins(board,dio);
    int numpins = dio==DIO1 ? DIO1_NUM_PINS : DIO2_NUM_PINS;
    int pin;

    for (pin=0; pin<numpins; pin++) {
        printf("Pin %d: %d\n",pin,(state&(1<<pin))?1:0);
    }
}

void ReadDirs (Board* board, DIOPort dio)
{
    int dirs    = board_get_dirs(board,dio);
    int numpins = dio==DIO1 ? DIO1_NUM_PINS : DIO2_NUM_PINS;
    int pin;

    printf("pins.input:");
    for (pin=0; pin<numpins; pin++) {
        if ((dirs & (1<<pin))==0) {
            printf(" %d",pin);
        }
    }
    printf("\n");

    printf("pins.output:");
    for (pin=0; pin<numpins; pin++) {
        if ((dirs & (1<<pin))!=0) {
            printf(" %d",pin);
        }
    }
    printf("\n");
}

void ReadJumpers (Board* board)
{
    int jp;

    for (jp=2; jp<=6; jp++) {
        printf("%d: %d\n",jp,board_get_jumper(board,jp));
    }
}

void ReadTS9700 (Board* board)
{
    int channel;
    int sample;
    int prev;
    int trial;
    const int maxTrials=10;

    for (channel=0; channel<TS9700_NUM_CHANNELS; channel++) {
        prev = board_get_adc_TS9700(board,channel);
        for (trial=0; trial<maxTrials; trial++) {
            sample = board_get_adc_TS9700(board,channel);
            if (abs(sample-prev)<5)
                break;
            prev=sample;
        }
        printf("channel.%d: %d\n",channel,sample);
    }
}


// Original code from Todd V.
// Read all five EP9301 ADC channels
void ReadEP9301 (Board* board)
{
    int channel;
    int sample;
    int average;
    float volts;
    const int NUM_SAMPLES = 4;

    for (channel=0; channel<EP9301_NUM_CHANNELS; channel++) {
        average=0;

        // Discard first two samples
        board_get_adc_EP9301(board,channel);
        board_get_adc_EP9301(board,channel);

        for (sample=0; sample<NUM_SAMPLES; sample++) {
            usleep(10000);
            average+=board_get_adc_EP9301(board,channel);
        }

        average /= NUM_SAMPLES;  
        if (average<0x7000)
            average+=0x10000;
        average -= 0x9E58;

        volts = ((float)average * 3.3) / 0xC350;

        printf("channel.%d: %3.3f V\n",channel,volts);
    }
}


// Read all eight router board analog inputs
void ReadRouterAnalog (Board* board)
{
    int channel;
    int sample;
    int average;
    float volts;
    int router_mux = 0;
    const int ROUTER_NUM_CHANNELS = 8;
    const int ROUTER_ADC_CHANNEL = 2;
    const int NUM_SAMPLES = 4;

    for (channel = 0; channel < ROUTER_NUM_CHANNELS; channel++) {
        average = 0;
        
        // Select the router board ADC input
        board_set_pin(board, DIO2, 0, router_mux & 1);
        board_set_pin(board, DIO2, 1, (router_mux & 2) >> 1);
        board_set_pin(board, DIO2, 2, (router_mux & 4) >> 2);
        
        // Discard first two samples
        board_get_adc_EP9301(board, ROUTER_ADC_CHANNEL);
        board_get_adc_EP9301(board, ROUTER_ADC_CHANNEL);

        for (sample=0; sample<NUM_SAMPLES; sample++) {
            usleep(10000);
            average += board_get_adc_EP9301(board, ROUTER_ADC_CHANNEL);
        }

        average /= NUM_SAMPLES;  
        if (average<0x7000)
            average+=0x10000;
        average -= 0x9E58;

        volts = ((float)average * 3.3) / 0xC350;

        printf("router.%d: %3.3f V\n", router_mux, volts);
        ++router_mux;
    }
}




int SetDir (Board* board, char* option[], int numOpts)
{
    DIOPort port;
    int pin = strtol(option[2],NULL,0);
    int dir;

    if (strcmp(option[3],"in")==0) {
        dir=0;
    } else if (strcmp(option[3],"out")==0) {
        dir=1;
    } else {
        printf("Unknown direction: %s\n",option[3]);
        return 0;
    }

    if (strcmp(option[1],"dio1")==0) {
        return board_set_dir(board,DIO1,pin,dir);
    } else if (strcmp(option[1],"dio2")==0) {
        return board_set_dir(board,DIO2,pin,dir);
    } else {
        printf("Unknown port\n");
        return 0;
    }

    return 1;
}


int SetDirs (Board* board, char* option[], int numOpts)
{
    DIOPort port;
    int dirs = strtol(option[2],NULL,0);

    if (strcmp(option[1],"dio1")==0) {
        return board_set_dirs(board,DIO1,dirs);
    } else if (strcmp(option[1],"dio2")==0) {
        return board_set_dirs(board,DIO2,dirs);
    } else {
        printf("Unknown port\n");
        return 0;
    }
}

int SetPin (Board* board, char* option[], int numOpts)
{
    DIOPort port;
    int pin = strtol(option[2],NULL,0);
    int state = ParseState(option[3]);

    if (strcmp(option[1],"dio1")==0) {
        return board_set_pin(board,DIO1,pin,state);
    } else if (strcmp(option[1],"dio2")==0) {
        return board_set_pin(board,DIO2,pin,state);
    } else {
        printf("Unknown port\n");
        return 0;
    }

    return 1;
}

int SetPins (Board* board, char* option[], int numOpts)
{
    DIOPort port;
    int states = strtol(option[2],NULL,0);
    char* buffer=option[1];

    if (strcmp(option[1],"dio1")==0) {
        return board_set_pins(board,DIO1,states);
    } else if (strcmp(option[1],"dio2")==0) {
        return board_set_pins(board,DIO2,states);
    } else {
        printf("Unknown port\n");
        return 0;
    }
}

int SetLED (Board* board, char* option[], int numOpts)
{
    int led = strcmp(option[1],"red")==0 ? RED : GREEN;
    int state = ParseState(option[2]);

    return board_set_led(board,led,state);
}

int SetEthernetPower (Board* board, char* option[], int numOpts)
{
    return board_set_ethernet_power(board,ParseState(option[1]));
}

int SetUSBPower (Board* board, char* option[], int numOpts)
{
    return board_set_usb_power(board,ParseState(option[1]));
}

int SetRS232Power (Board* board, char* option[], int numOpts)
{
    return board_set_rs232_power(board,ParseState(option[1]));
}

int SetPC104Power (Board* board, char* option[], int numOpts)
{
    return board_set_pc104_power(board,ParseState(option[1]));
}

int SetCPUSpeed (Board* board, char* option[], int numOpts)
{
    int speed = ParseSpeed(option[1]);

    if (speed == -1) {
        printf("Unknown speed: %s\n",option[1]);
        return 0;
    }

    return board_set_cpu_speed(board,speed);
}

/*------------------------------------------------------------------------*/

void PrintUsage()
{
    int k;

    printf("\n");
    printf("SBC Control Program, version %s\n",VERSION);
    printf("Usage sbcctl [options] command, where commnad is one of:\n");
    printf("\n");

    printf("    %15s  %-25s  Description\n\n","Command","Options");

    for (k=0; k<NumCommands; k++) {
        printf("    %15s  %-25s",Commands[k].name,Commands[k].usage);
        printf(" - %s\n",Commands[k].desc);
    }

    printf("\n");
    printf("<dio>   - DIO1 or DIO2\n");
    printf("<dir>   - in or out\n");
    printf("<state> - 0|off or 1|on\n");
    printf("<led>   - red or green\n");
    printf("<speed> - min, 42, 166, max\n");

    printf("\n");
    printf("Options:\n");
    printf("  -v    - print debugging info\n");
    printf("  -m    - print Start/Finish markers\n");
    printf("  -h    - print this help screen\n");
    printf("\n");
}

int ProcessCommand(int argc, char* argv[])
{
    int     k,j;
    int     result;
    int     verbose=0;
    int     marker=0;
    Board*  board;

    int c;
    int index;

    opterr = 0;
    //log_write("ProcessCommand: parsing cmd options");
    while ((c=getopt(argc,argv,"vmhd"))!=-1) {
        switch(c) {
            case 'v':
                verbose=1;
                break;
            case 'm':
                marker=1;
                break;
            case 'h':
                PrintUsage();
                return 1;
            case '?':
                if (isprint(optopt)) {
                    fprintf(stderr,"Unknown option `-%c'.\n",optopt);
                } else {
                    fprintf(stderr,"Unknown option character `\\x%x'.\n",
                        optopt);
                }
                return 0;
            default:
                return 0;
        }
    }

    if (argc<=optind) {
        PrintUsage();
        return 0;
    }

    for (k=optind; k<argc; k++) {
        LowerCase(argv[k]);
    }

    for (k=0; k<NumCommands; k++) {

        if (strcmp(argv[optind],Commands[k].name)==0) {
            if (argc-optind <= Commands[k].numOptions) {
                fprintf(stderr,"Not enough parameters\n");
                fprintf(stderr,"  Usage: sbcctl %s\n",Commands[k].usage);
                return 0;
            }

            board = board_new();

            if (marker) {
                printf("** Start **\n");
            }
            //log_write("ProcessCommand: calling Commands[k].callback");
            result = Commands[k].callback(board,argv+optind,argc-optind);

            if (!result) {
                fprintf(stderr,"Error\n");
            } else {
                if (marker) {
                    printf("OK\n");
                }
            }

            if (marker) {
                printf("** Finished **\n");
            }
            //log_write("ProcessCommand: calling board_delete");
            board_delete(board);

            return result;
        }
    }

    fprintf(stderr,"Command not recognized: %s\n",argv[optind]);
    fprintf(stderr,"  (Use \"help\" for a list of valid commands)\n");

    return 0;
}



// Return non-zero if the file exists
int file_exists(const char *filename)
{
	FILE *file;
	
	file = fopen(filename, "r");
	if (file){
		fclose(file);
		return 1;
	}
	return 0;
}

int main (int argc, char* argv[])
{
	int	result;
	
    //log_open(LOG_FILE_DIR, LOG_FILE_NAME, LOG_FILE_MAX_SIZE);
    //log_write("main: entering main");
	
	// If the dio1 driver is not installed,
	//  install it now
	//log_write("main: calling file_exists");
	if (!file_exists("/dev/dio1")) {
		system("/aal-pip/field/bin/install_dio1");
		//printf("Installed dio1 driver\n");
	}
    /* This program has 20 seconds to complete. */
    alarm(20);

    //log_write("main: calling ProcessCommand");
    result = ProcessCommand(argc,argv);
    //close_dio1_drvr();
    //log_write("main: exiting main");
    //log_close();
    return result ? EXIT_SUCCESS : EXIT_FAILURE; 
}





