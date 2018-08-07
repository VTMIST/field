#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <string.h>
#include <sys/types.h>
#include <assert.h>

#include "board.h"
#include "dio1.h"

static unsigned char*   board_mmap              (Board* self, off_t offset);
static int              board_busy_adc_EP9301   (Board* self);
static void             board_xdio_set_mode     (Board* self, int mode);
static int 				dio1_drvr_fd = -1;

/* Constants */

#define NUM_DIO1_PINS	7

/* Offsets */

#define SSPCR1              0x04
#define SSPCPSR             0x10
#define CHIP_SELECT_DATA    0x30
#define CHIP_SELECT_DDR     0x34
#define SSP_DATA            0x08
#define CMD_REG             0x160
#define RESULT_REG          0x162
#define SERIAL_BASE         0x3e8
#define SERIAL_MCR          0x04

#define ADC_CH0             0x0608
#define ADC_CH1             0x0680
#define ADC_CH2             0x0640
#define ADC_CH3             0x0620
#define ADC_CH4             0x0610

/* Function Prototypes */
static int open_dio1_drvr(void);

static int get_dio1_dirs(void);
static int get_dio1_pins(void);

static int get_dio1_pin(int pin);
static int get_dio1_dir(int pin);

static void set_dio1_dirs(int dirs);
static void set_dio1_pins(int pin_states);

static void set_dio1_pin(int pin, int pin_state);
static void set_dio1_dir(int pin, Direction dir);



/*-----------------------------------------------------------------------
 * Memory access functions
 *---------------------------------------------------------------------*/

void poke8 (unsigned char* addr, unsigned char data)
{
    *addr = data;
}

void poke16 (unsigned char* addr, unsigned short data)
{
    *(unsigned short*)addr = data;
}

void poke32 (unsigned char* addr, unsigned int data)
{
    *(unsigned int*)addr = data;
}

unsigned char peek8 (unsigned char* addr)
{
    return *addr;
}

unsigned short peek16 (unsigned char* addr)
{
    return *((unsigned short*)addr);
}

unsigned int peek32 (unsigned char* addr)
{
    return *((unsigned int*)addr);
}

void poke_bit8 (unsigned char* addr, int bit, int state)
{
    unsigned char mask = 1<<bit;

    poke8(addr, (peek8(addr) & ~mask) | (state ? mask : 0));
}

void poke_bit16 (unsigned char* addr, int bit, int state)
{
    unsigned short mask = 1<<bit;
    poke16(addr, (peek16(addr) & ~mask) | (state ? mask : 0));
}

void poke_bit32 (unsigned char* addr, int bit, int state)
{
    unsigned int mask = 1<<bit;
    poke32(addr, (peek32(addr) & ~mask) | (state ? mask : 0));
}

int peek_bit8 (unsigned char* addr, int bit)
{
    unsigned char mask = 1<<bit;

    return peek8(addr) & mask ? 1 : 0;
}

int peek_bit16 (unsigned char* addr, int bit)
{
    unsigned short mask = 1<<bit;

    return peek16(addr) & mask ? 1 : 0;
}

int peek_bit32 (unsigned char* addr, int bit)
{
    unsigned int mask = 1<<bit;

    return peek32(addr) & mask ? 1 : 0;
}

void set_bit8 (unsigned char* addr, int bit)
{
    poke_bit8(addr,bit,1);
}

void clr_bit8 (unsigned char* addr, int bit)
{
    poke_bit8(addr,bit,0);
}

void set_bit16 (unsigned char* addr, int bit)
{
    poke_bit16(addr,bit,1);
}

void clr_bit16 (unsigned char* addr, int bit)
{
    poke_bit16(addr,bit,0);
}

void set_bit32 (unsigned char* addr, int bit)
{
    poke_bit32(addr,bit,1);
}

void clr_bit32 (unsigned char* addr, int bit)
{
    poke_bit32(addr,bit,0);
}



/*-----------------------------------------------------------------------
 * Board functions
 *---------------------------------------------------------------------*/

Board* board_new()
{
    Board* self = calloc(1,sizeof(Board));

    if (!self)
        return NULL;

    self->mem = open("/dev/mem",O_RDWR|O_SYNC);

    if (self->mem == -1) {
        perror("/dev/mem");
        free(self);
        return NULL;
    }

    self->tsstatus  = board_mmap(self,0x10800000);
    self->tsjp6     = board_mmap(self,0x22800000);
    self->gpio      = board_mmap(self,0x80840000);
    self->tsxdio    = board_mmap(self,0x12C00000);
    self->tschipsel = board_mmap(self,0x80840000);
    self->ssp     = board_mmap(self,0x808A0000);
    self->ts9700    = board_mmap(self,0x11C00000);
    self->adcreg    = board_mmap(self,0x80900000);
    self->syscon    = board_mmap(self,0x80930000);
    self->pwrcon    = board_mmap(self,0x12000000);
    self->usbreg    = board_mmap(self,0x80020000);
    self->sdramreg  = board_mmap(self,0x80060000);

    return self;
}

void board_delete(Board* self)
{
    if (!self) {
        return;
    }

    close(self->mem);

    free(self);
}

unsigned char* board_mmap (Board* self, off_t addr)
{
    unsigned char* page;
    int retries = 0;
    
    while (retries++ < 3)
    {
        page = mmap(0,getpagesize(),
                    PROT_READ|PROT_WRITE,MAP_SHARED,
                    self->mem,addr);
        if (page != MAP_FAILED)
        {
            return page;
        }
    }
    assert(page != MAP_FAILED);
    return page;
}

int board_get_jumper (Board* self, int jp)
{
    switch(jp) {
        case 2: return ((*self->tsstatus & 0x01) ? 1 : 0);
        case 3: return ((*self->tsstatus & 0x02) ? 1 : 0);
        case 4: return ((*self->tsstatus & 0x08) ? 0 : 1);
        case 5: return ((*self->tsstatus & 0x10) ? 0 : 1);
        case 6: return ((*self->tsjp6    & 0x01) ? 1 : 0);
    }
    return 0;
}

void board_xdio_set_mode(Board* self, int mode)
{
    self->tsxdio[0] = (self->tsxdio[0] & ~(0xC8)) | ((mode & 0x03) << 6);
}

int board_set_led (Board* self, LED led, State state)
{
    poke_bit8(self->gpio+0x20,led,state);

    return 1;
}

int board_get_led (Board* self, LED led)
{
    return peek_bit8(self->gpio+0x20,led);
}

int board_set_pins (Board* self, DIOPort port, int state)
{
    if (port==DIO1) {
    	set_dio1_pins(state);
        //self->gpio[0x04] = state & 0xFF;
        //poke_bit8(self->gpio+0x30,1,state & 0x100);
    } else {
        board_xdio_set_mode(self,0);
        self->tsxdio[2]=state;
    }

    return 1;
}

int board_set_pin (Board* self, DIOPort port, int pin, State state)
{
    if (port==DIO1) {
        if (pin==8) {
            //poke_bit8(self->gpio+0x30,1,state);	// gps_pps uses this pin for PPS interrupt input
            printf("board.board_set_pin: Attempted to control DIO1 bit 8\n");
        } else {
        	set_dio1_pin(pin, state);
            //poke_bit8(self->gpio+0x04,pin,state);
        }
    } else {
        board_xdio_set_mode(self,0);
        poke_bit8(self->tsxdio+0x02,pin,state);
    }
    return 1;
}


int board_get_pins (Board* self, DIOPort port)
{
    int portB = self->gpio[0x04];
    int portF = (self->gpio[0x30] & 0x02) >> 1;

    if (port==DIO1) {
    	return get_dio1_pins();
        //return (portF << 8) | portB;
    } else {
        board_xdio_set_mode(self,0);
        return self->tsxdio[2];
    }
}


int board_get_pin (Board* self, DIOPort port, int pin)
{
    int pins = board_get_pins(self,port);

    return (pins & (1<<pin)) ? 1 : 0;
}


int board_get_dirs (Board* self, DIOPort port)
{
    int portB = self->gpio[0x14];
    int portF = (self->gpio[0x34] & 0x02) >> 1;

    if (port==DIO1) {
    	return get_dio1_dirs();
        //return (portF << 8) | portB;
    } else {
        board_xdio_set_mode(self,0);
        return self->tsxdio[1];
    }
}

int board_set_dir (Board* self, DIOPort port, int pin, Direction dir)
{
    if (port==DIO1) {
        if (pin==8) {
            //poke_bit8(self->gpio+0x34,1,dir==OUTPUT);
        } else {
        	set_dio1_dir(pin, dir);
            //poke_bit8(self->gpio+0x14,pin,dir==OUTPUT);
        }
    } else {
        board_xdio_set_mode(self,0);
        poke_bit8(self->tsxdio+1,pin,dir==OUTPUT);
    }

    return 1;
}

int board_set_dirs (Board* self, DIOPort port, int dirs)
{
    if (port==DIO1) {
    	set_dio1_dirs(dirs);
        //self->gpio[0x14] = dirs & 0xFF;
        //poke_bit8(self->gpio+0x34,1,dirs&0x100);
    } else {
        board_xdio_set_mode(self,0);
        self->tsxdio[1] = dirs;
    }

    return 1;
}

float board_get_temp (Board* self)
{
	unsigned long val;
	double temp;
	unsigned char isNegative = 0;

	/*
	 The EP9301 Users Manual says the following algorithm must
	 be used to configure and enable the SPI bus
	 http://www-s.ti.com/sc/ds/tmp124.pdf
	*/

	/* 1.)	Set enable bit(SSE) in register SSPCR1*/
    poke32(self->ssp+SSPCR1,0x10);

	/* 2.)	Write other SSP config registers(SSPCR0 & SSPCPSR)*/
	poke32(self->ssp, 0x0F );
	poke32(self->ssp + SSPCPSR, 0xFE );

	/* 3.)	Clear the enable bit(SSE) in register SSPCR1*/
    poke32(self->ssp+SSPCR1,0);
	//usleep(10000); //let the lines settle

	/* 4.)	Set the enable bit(SSE) in register SSPCR1*/
    poke32(self->ssp+SSPCR1,0x10);

	/* Done with configuration now lets read the current temp...*/

	//enable the chip select
    set_bit32(self->tschipsel+CHIP_SELECT_DDR,2);
    clr_bit32(self->tschipsel+CHIP_SELECT_DATA,2);

	//send read temp command
	poke32(self->ssp+SSP_DATA, 0x8000);
	usleep(1000);

	//disable chip select
    clr_bit32(self->tschipsel+CHIP_SELECT_DDR,2);

	//read the temp
	val = peek32(self->ssp+SSP_DATA);

	//Lets check if the value is negative
	if( val <= 0xFFFF && val >= 0xE487 )
	{
		//perform two's complement
		val = (~val + 1) & 0xFFFF;
		isNegative = 1;

	} else if( val <= 0x4B08 && val >= 0xE486 )
	{
		printf("FAIL, invalid register value(out of range)...\n");
		return 0;
	}

	if( val >= 0x3E88 && val <= 0x4B07)
	{
		temp = val / 128.046;

	} else if( val >= 0xC88 && val <= 0x3E87 )
	{
		temp = val / 128.056;

	} else if( val >= 0x10 && val <= 0xC87 )
	{
		temp = val / 128.28;
	} else// => val >= 0x00 && val <= 0x0F
	{
		temp = val / 240;
	}

	if (isNegative)
		temp = -temp;

    return temp;        /* Deg C */
}

int board_init_adc_TS9700 (Board* self)
{
    return self->ts9700[CMD_REG+1]==0x97;
}

int board_get_adc_TS9700 (Board* self, int channel)
{
    int bit7 = 1 << 7;
    int value;

    self->ts9700[CMD_REG] = channel;

    while (!(self->ts9700[CMD_REG] & bit7)) {
    }

    return peek16(self->ts9700+RESULT_REG);
}

int board_init_adc_EP9301 (Board* self)
{
    /* Unlock and set TSEN */

    poke32(self->syscon+0xC0,0xAA);
    set_bit32(self->syscon+0x90,31);

    /* Unlock and set ADCEN */

    poke32(self->syscon+0xC0,0xAA);
    set_bit32(self->syscon+0x80,17);

    /* Unlock and clear ADCPD */

    poke32(self->syscon+0xC0,0xAA);
    clr_bit32(self->syscon+0x80,2);

    return 1;
}

int board_get_adc_EP9301 (Board* self, int channel)
{
    switch(channel) {
        case 0: channel = ADC_CH0;  break;
        case 1: channel = ADC_CH1;  break;
        case 2: channel = ADC_CH2;  break;
        case 3: channel = ADC_CH3;  break;
        case 4: channel = ADC_CH4;  break;
    }

    /* Unlock and write channel to ADCSwitch reg */
    poke32(self->adcreg+0x20, 0xAA);
    poke32(self->adcreg+0x18, channel);

    /* poll ADCResult */
    while(board_busy_adc_EP9301(self));

    /* read result from data register */

    return peek32(self->adcreg+0x08) & 0xFFFF;
}

int board_busy_adc_EP9301 (Board* self)
{
    return peek_bit32(self->adcreg+0x08,31);
}

int board_set_ethernet_power (Board* self, int enable)
{
    if (enable) {
        set_bit8(self->gpio+0x40,2);
    } else {
        set_bit8(self->gpio+0x44,2);
        clr_bit8(self->gpio+0x40,2);
    }

    return 1;
}

int board_get_ethernet_power (Board* self)
{
    return peek_bit8(self->gpio+0x40,2);
}

int board_set_usb_power (Board* self, int enable)
{
    if (enable) {
        set_bit32(self->syscon+4,28);
        clr_bit8(self->usbreg+4,6);
        set_bit8(self->usbreg+4,7);
        set_bit8(self->pwrcon,1);
    } else {
        clr_bit32(self->syscon+4,28);
        clr_bit8(self->pwrcon,1);
    }

    return 1;
}

int board_get_usb_power (Board* self)
{
    return peek_bit32(self->syscon+4,28) && peek_bit32(self->pwrcon,1);
}

int board_set_pc104_power (Board* self, int enable)
{
    if (enable) {
        set_bit8(self->pwrcon,3);
    } else {
        clr_bit8(self->pwrcon,3);
    }

    return 1;
}

int board_get_pc104_power (Board* self)
{
    return peek_bit8(self->pwrcon,3);
}

int board_set_rs232_power (Board* self, int enable)
{
    if (enable) {
        set_bit8(self->pwrcon,0);
    } else {
        clr_bit8(self->pwrcon,0);
    }

    return 1;
}

int board_get_rs232_power (Board* self)
{
    return peek_bit8(self->pwrcon,0);
}

int board_set_cpu_speed (Board* self, Speed speed)
{
    switch (speed) {
        case CPU_MAX:   poke32(self->syscon+0x20,0x02a4bb36);
                        poke32(self->sdramreg+0x08,0x30D);
                        break;
        case CPU_166:   poke32(self->syscon+0x20,0x02b4fa5a);
                        poke32(self->sdramreg+0x08,0x203);
                        break;
        case CPU_42:    poke32(self->syscon+0x20,0x0296fa5a);
                        poke32(self->sdramreg+0x08,0x144);
                        break;
        case CPU_MIN:   poke32(self->syscon+0x20,0);
                        poke32(self->sdramreg+0x08,0x073);
                        break;
    }

    return 1;
}

int board_get_cpu_speed (Board* self)
{
    switch (peek32(self->syscon+0x20)) {
        case 0x02a4bb36: return CPU_MAX;
        case 0x02b4fa5a: return CPU_166;
        case 0x0296fa5a: return CPU_42;
        case 0:          return CPU_MIN;
        default:         return -1;
    }
}


// Set the states of DIO1 bits 0 - 6.
// Use the dio1 driver to avoid conflict
//  with the gps_pps driver which controls
//  DIO1 bit 7 (pseudo PPS).
static void set_dio1_pins(int pin_states)
{
	int	pin;

	for (pin = 0; pin <= NUM_DIO1_PINS; ++pin) {
		set_dio1_pin(pin, (pin_states & 1));
		pin_states = pin_states >> 1;
	} 	
}


// Return the value of DIO1 bits 0 - 6
// DIO 7 and 8 are controlled by the gps_pps driver.
static int get_dio1_pins(void)
{
	struct bit_info		my_bit;
	int pin_states = 0;
	int pin;
	
	for (pin = NUM_DIO1_PINS - 1; pin >= 0; --pin) {
		pin_states = pin_states << 1;
		pin_states = pin_states | get_dio1_pin(pin);
	} 	
	return pin_states;
	// NOTE: dio1 driver is closed in main()
}


// Set the directions of a DIO1 bits 0 - 6.
// Use the dio1 driver to avoid conflict
//  with the gps_pps driver which controls
//  DIO1 bit 7 (pseudo PPS).static void set_dio1_dir(int pin, Direction dir)
static void set_dio1_dirs(int pin_dirs)
{
	int		pin;
	
	for (pin = 0; pin <= NUM_DIO1_PINS; ++pin) {
		set_dio1_dir(pin, (pin_dirs & 1));
		pin_dirs = pin_dirs >> 1;
	} 	
	// NOTE: dio1 driver is closed in main()
}


// Return the directions (in or out) of DIO1 bits 0 - 6
// DIO 7 and 8 are controlled by the gps_pps driver.
static int get_dio1_dirs(void)
{
	struct bit_info		my_bit;
	int pin_dirs = 0;
	int pin;
	
	for (pin = NUM_DIO1_PINS - 1; pin >= 0; --pin) {
		pin_dirs = pin_dirs << 1;
		pin_dirs = pin_dirs | get_dio1_dir(pin);
	} 	
	return pin_dirs;
	// NOTE: dio1 driver is closed in main()
}


// Set the state of a DIO1 bit (0 - 6).
// Use the dio1 driver to avoid conflict
//  with the gps_pps driver which controls
//  DIO1 bit 7 (pseudo PPS).
static void set_dio1_pin(int pin, int pin_state)
{
	struct bit_info		my_bit;
	
	if (!open_dio1_drvr()) {
		return;
	}
	my_bit.number = pin;
	my_bit.value = pin_state;
	//printf("set_dio1_pin: set pin %d state to %d\n", pin, pin_state);
	ioctl(dio1_drvr_fd, DIO1_IOC_SET_BIT_VALUE, &my_bit);
	// NOTE: dio1 driver is closed in main()
}


// Set the direction of a DIO1 bit (0 - 6).
// Use the dio1 driver to avoid conflict
//  with the gps_pps driver which controls
//  DIO1 bit 7 (pseudo PPS).
static void set_dio1_dir(int pin, Direction dir)
{
	struct bit_info		my_bit;
	
	if (!open_dio1_drvr()) {
		return;
	}
	my_bit.number = pin;
	my_bit.dir = dir;
	my_bit.value = 0;
	//printf("set_dio1_dir: set pin %d dir to %d\n", pin, dir);
	ioctl(dio1_drvr_fd, DIO1_IOC_SET_BIT_DIR, &my_bit);
	// NOTE: dio1 driver is closed in main()
}


// Get the state of a DIO1 bit (0 - 6).
// Use the dio1 driver to avoid conflict
//  with the gps_pps driver which controls
//  DIO1 bit 7 (pseudo PPS).
static int get_dio1_pin(int pin)
{
	struct bit_info		my_bit;
	
	if (!open_dio1_drvr()) {
		return;
	}
	my_bit.number = pin;
	ioctl(dio1_drvr_fd, DIO1_IOC_GET_BIT_VALUE, &my_bit);
	//printf("get_dio1_pin: pin %d value is %d\n", pin, my_bit.value);
	return my_bit.value;
	// NOTE: dio1 driver is closed in main()
}


// Get the direction of a DIO1 bit (0 - 6).
// Use the dio1 driver to avoid conflict
//  with the gps_pps driver which controls
//  DIO1 bit 7 (pseudo PPS).
static int get_dio1_dir(int pin)
{
	struct bit_info		my_bit;
	
	if (!open_dio1_drvr()) {
		return;
	}
	my_bit.number = pin;
	ioctl(dio1_drvr_fd, DIO1_IOC_GET_BIT_DIR, &my_bit);
	//printf("get_dio1_dir: pin %d dir is %d\n", pin, my_bit.dir);
	return my_bit.dir;
	// NOTE: dio1 driver is closed in main()
}



// Open the dio1 driver
// Store the file descriptor in _pps_drvr_fd
// Return 0 if error, non-zero if successful.
static int open_dio1_drvr(void)
{
    int fd;
    const char *dev_name = "/dev/dio1";
	
	if (dio1_drvr_fd > 0)
	{
		return 1;
	}
	fd = open(dev_name, O_RDWR);
	if (fd < 0)
	{
        perror("open_dio1_drvr: Could not open the dio1 driver ");
        dio1_drvr_fd = -1;
        return 0;
	}
	dio1_drvr_fd = fd;
	return 1;
}


// Close the dio1 driver
void close_dio1_drvr(void)
{
    if (dio1_drvr_fd > 0)
    {
        close(dio1_drvr_fd);
        dio1_drvr_fd = -1;
    }
}




