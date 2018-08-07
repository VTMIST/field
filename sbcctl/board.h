#ifndef BOARD_H
#define BOARD_H

#define DIO1_NUM_PINS   7
#define DIO2_NUM_PINS   8
#define TS9700_NUM_CHANNELS 8
#define EP9301_NUM_CHANNELS 5

typedef enum {
    DIO1,
    DIO2
} DIOPort;

typedef enum {
    INPUT,
    OUTPUT
} Direction;

typedef enum {
    OFF,
    ON
} State;

typedef enum {
    GREEN,
    RED
} LED;

typedef enum {
    CPU_MIN,
    CPU_42,
    CPU_166,
    CPU_MAX
} Speed;

typedef struct {
    int                 mem;
    unsigned char*      tsstatus;
    unsigned char*      tsjp6;
    unsigned char*      gpio;
    unsigned char*      tsxdio;
    unsigned char*      tschipsel;
    unsigned char*      ssp;
    unsigned char*      ts9700;
    unsigned char*      adcreg;
    unsigned char*      syscon;
    unsigned char*      pwrcon;
    unsigned char*      usbreg;
    unsigned char*      sdramreg;
} Board;

Board*  board_new       ();
void    board_delete    (Board* self);

int     board_set_pin   (Board* self, DIOPort port, int pin, State state);
int     board_set_pins  (Board* self, DIOPort port, int states);

int     board_set_dir   (Board* self, DIOPort port, int pin, Direction dir);
int     board_set_dirs  (Board* self, DIOPort port, int dirs);

int     board_set_led   (Board* self, LED led, State state);
int     board_get_led   (Board* self, LED led);

int     board_set_ethernet_power(Board* self, int enable);
int     board_get_ethernet_power(Board* self);

int     board_set_usb_power     (Board* self, int enable);
int     board_get_usb_power     (Board* self);

int     board_set_pc104_power   (Board* self, int enable);
int     board_get_pc104_power   (Board* self);

int     board_set_rs232_power   (Board* self, int enable);
int     board_get_rs232_power   (Board* self);

int     board_set_cpu_speed     (Board* self, Speed speed);
int     board_get_cpu_speed     (Board* self);

int     board_get_jumper        (Board* self, int jp);
int     board_get_pin           (Board* self, DIOPort port, int pin);
int     board_get_pins          (Board* self, DIOPort port);
int     board_get_dirs          (Board* self, DIOPort port);
float   board_get_temp          (Board* self);
int     board_init_adc_TS9700   (Board* self);
int     board_get_adc_TS9700    (Board* self, int channel);
int     board_init_adc_EP9301   (Board* self);
int     board_get_adc_EP9301    (Board* self, int channel);

int     board_get_status        (Board* self);

void	close_dio1_drvr			(void);

#endif
