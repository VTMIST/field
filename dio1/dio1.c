/*
	DIO1 Digital I/O Driver
	Controls DIO1 bits 0- 6.
	All are configured as outputs.
	All are set to 0 at driver init time.
	DIO1 bit 7 is controlled by the gps_pps driver.
*/

#include <linux/module.h>       /* for modules */
#include <linux/fs.h>           /* file_operations */
#include <linux/uaccess.h>      /* copy_(to,from)_user */
#include <linux/init.h>         /* module_init, module_exit */
#include <linux/slab.h>         /* kmalloc */
#include <linux/cdev.h>         /* cdev utilities */
#include <linux/interrupt.h>
#include <linux/gpio.h>
#include <linux/ioctl.h>
#include <linux/timer.h>
#include <linux/param.h>
#include <linux/proc_fs.h>

#include "dio1.h"

#define true 1
#define false 0

#define IN	0
#define OUT	1

typedef int boolean;

// The ID number for the GPIO that
//  serves as the PPS interrupt input.
// It is GPIO Port F, Pin 1.
// See Documentation/gpio.txt for details.
// The bit names are defined in:
/*
~/projects/tincan/buildroot-obuoy-mark2/project_build_arm/obuoy-mark2/linux-2.6.29.6/arch/arm/mach-ep93xx/include/mach/gpio.h
*/
#define PPS_GPIO 		EP93XX_GPIO_LINE_MCCD1

#define DEV_NAME "dio1"

// The ID number for the GPIO that
//  controls DIO1 bit 0.
// See Documentation/gpio.txt for details.
// The GPIO bit names are defined in:
/*
~/projects/tincan/buildroot-obuoy-mark2/project_build_arm/obuoy-mark2/linux-2.6.29.6/arch/arm/mach-ep93xx/include/mach/gpio.h
*/
#define DIO1_BIT_0_GPIO EP93XX_GPIO_LINE_EGPIO8
#define NUM_DIO1_BITS 7

static dev_t _first_dev;
static unsigned int _dev_count = 1;
static int _drvr_major_num = 101;
static int _drvr_minor_num = 0;
static struct cdev *_drvr_cdev;

struct dio_info_struct {
	int			dir;		// 0 is input, 1 is output
	int			value;
	boolean		allocated;
	int			gpio;
};
static struct dio_info_struct _dio_info[NUM_DIO1_BITS];
		
		
// Function prototypes
static int drvr_open (struct inode *inode,
					  struct file *file);
static int drvr_ioctl (struct inode *inode,
						struct file *file,
						unsigned int cmd,
						unsigned long arg);
static int drvr_release (struct inode *inode,
						 struct file *file);
static ssize_t drvr_read (struct file *file,
							char __user *buf,
							size_t lbuf,
							loff_t *ppos);
static ssize_t drvr_write(struct file *file,
						const char __user *buf,
						size_t lbuf,
              			loff_t * ppos);
static int drvr_read_procmem(char *buf,
							 char **start,
							 off_t offset,
							 int count,
							 int *eof,
							 void *data);
static boolean allocate_all_dio1_gpio(void);
static boolean allocate_dio1_gpio(int bit_num);
static void free_all_dio1_gpio(void);

static void set_dio1_bit_dir(struct bit_info *user_buf);
static void get_dio1_bit_dir(struct bit_info *user_buf);
static void set_dio1_bit_value(struct bit_info *user_buf);
static void get_dio1_bit_value(struct bit_info *user_buf);

							 						
static const struct file_operations drvr_fops = {
    .owner = THIS_MODULE,
    .read = drvr_read,
    .write = drvr_write,
    .ioctl = drvr_ioctl,
    .open = drvr_open,
    .release = drvr_release
};


static int drvr_open (struct inode *inode,
					  struct file *file)
{
    return 0;
}


static int drvr_release (struct inode *inode,
						 struct file *file)
{
    return 0;
}


static ssize_t drvr_read (struct file *file,
							char __user *buf,
							size_t lbuf,
							loff_t *ppos)
{
	return 0;
}


static ssize_t drvr_write(struct file *file,
						const char __user *buf,
						size_t lbuf,
              			loff_t * ppos)
{
	return 0;
}

static int __init mod_init (void)
{
    int bit_num;
    
    memset(_dio_info, 0, sizeof(_dio_info));
	for (bit_num = 0; bit_num < NUM_DIO1_BITS; ++bit_num)
    {
        _dio_info[bit_num].dir = OUT;
        _dio_info[bit_num].value = 0;
    }
    
    if (!allocate_all_dio1_gpio())
    {
    	printk (KERN_INFO "dio1.mod_init: %s: Could not allocate GPIO output\n", DEV_NAME);
    	return -EIO;
    }
    if (!create_proc_read_entry(DEV_NAME, 0, NULL, drvr_read_procmem, NULL))
    {
    	free_all_dio1_gpio();
    	printk (KERN_INFO "dio1.mod_init: %s: create_proc_read_entry failed\n", DEV_NAME);
    	return -EIO;
    }
    _first_dev = MKDEV (_drvr_major_num, _drvr_minor_num);
    register_chrdev_region (_first_dev, _dev_count, DEV_NAME);
    _drvr_cdev = cdev_alloc ();
    cdev_init (_drvr_cdev, &drvr_fops);
    cdev_add (_drvr_cdev, _first_dev, _dev_count);
    //printk (KERN_INFO "Registered driver %s, major = %d, minor = %d\n",
    //        DEV_NAME, MAJOR(_first_dev), MINOR(_first_dev));
    return 0;
}


static void __exit mod_exit (void)
{
    free_all_dio1_gpio();
    remove_proc_entry(DEV_NAME, NULL);
    cdev_del (_drvr_cdev);
    unregister_chrdev_region (_first_dev, _dev_count);
    //printk (KERN_INFO "Unregistered driver %s\n",
    //        DEV_NAME);
}


// Allocate all the GPIO pins used for DIO1.0 through DIO1.6
static boolean allocate_all_dio1_gpio(void)
{
	int bit_num;

	for (bit_num = 0; bit_num < NUM_DIO1_BITS; ++bit_num) {
		if (!allocate_dio1_gpio(bit_num)) {
			free_all_dio1_gpio();
			printk(KERN_INFO "dio1.allocate_all_dio1_gpio: failed to allocate bit %d\n", bit_num);
			return false;	
		}
	}
	return true;
}


// Allocate a single GPIO pin used for DIO1.0 through DIO1.6
static boolean allocate_dio1_gpio(int bit_num)
{
	int result;
	int gpio_num = DIO1_BIT_0_GPIO + bit_num;
	
	if ((bit_num < 0) || (bit_num >= NUM_DIO1_BITS)) {
		return false;
	}
	_dio_info[bit_num].allocated = gpio_num;	
	_dio_info[bit_num].gpio = DIO1_BIT_0_GPIO + bit_num;
	if (!gpio_is_valid(gpio_num))
	{
		printk(KERN_INFO "dio1.allocate_dio1_gpio: gpio_is_valid failed\n");
		return false;
	}
	if ((result = gpio_request(gpio_num, DEV_NAME)) != 0)
	{
		printk(KERN_INFO "dio1.allocate_dio1_gpio: gpio_request failed %d\n", result);
		return false;
	}
	if (_dio_info[bit_num].dir == IN) {
		result = gpio_direction_input(gpio_num);
	} else {
		result = gpio_direction_output(gpio_num, _dio_info[bit_num].value);
	}	
	if (result != 0)
	{
		gpio_free(gpio_num);
		printk(KERN_INFO "dio1.allocate_dio1_gpio: gpio_direction_x failed %d\n", result);
		return false;
	}
	_dio_info[bit_num].allocated = true;
	return true;
}


// Deallocate all the GPIO pins used for DIO1.0 through DIO1.6
static void free_all_dio1_gpio(void)
{	
	int bit_num;

	for (bit_num = 0; bit_num < NUM_DIO1_BITS; ++bit_num) {
		if (_dio_info[bit_num].allocated) {
			gpio_free(DIO1_BIT_0_GPIO + bit_num);
			_dio_info[bit_num].allocated = false;
		}
	}
}


static int drvr_ioctl (struct inode *inode,
						struct file *file,
						unsigned int cmd,
						unsigned long arg)
{
	int err = 0;
	
    //printk (KERN_INFO "IOCTL cmd received: %s:\n", DEV_NAME);
    if (_IOC_TYPE(cmd) != DIO1_IOC_MAGIC) return ENOTTY;
    if (_IOC_NR(cmd) > DIO1_IOC_MAX_NR) return ENOTTY;
    
    // Validate user-supplied pointers.
    // Remember that access_ok assumes the kernel's R/W point
    // of view and IOC_DIR assumes the user's R/W point of view.
    if (_IOC_DIR(cmd) & _IOC_READ)
    	err = !access_ok(VERIFY_WRITE, (void __user *)arg, _IOC_SIZE(cmd));
    else if (_IOC_DIR(cmd) & _IOC_WRITE)
    	err = !access_ok(VERIFY_READ, (void __user *)arg, _IOC_SIZE(cmd));
    if (err) return -EFAULT;
    
    switch(cmd)
    {
		case DIO1_IOC_SET_BIT_DIR:
			set_dio1_bit_dir((struct bit_info *) arg);			
			break;
		case DIO1_IOC_GET_BIT_DIR:
			get_dio1_bit_dir((struct bit_info *) arg);			
			break;
		case DIO1_IOC_SET_BIT_VALUE:
			set_dio1_bit_value((struct bit_info *) arg);
			break;
		case DIO1_IOC_GET_BIT_VALUE:
			get_dio1_bit_value((struct bit_info *) arg);
			break;
    	default:
    		return -EFAULT;
    }   
	return 0;
}



// Set the value of a DIO1 bit.
static void set_dio1_bit_value(struct bit_info *user_buf)
{
	struct bit_info 	user_bit_info;
	int					bit_num;
	int                 gps_pps_irq;
	
	copy_from_user(&user_bit_info, user_buf, sizeof(struct bit_info));
	bit_num = user_bit_info.number;
	if ((bit_num < 0) || (bit_num >= NUM_DIO1_BITS)) {
		return;
	}
	if (_dio_info[bit_num].dir == OUT) {
		_dio_info[bit_num].value = user_bit_info.value;
	    // disable the GPS_PPS interrupt since it uses gpio
		gps_pps_irq = gpio_to_irq(PPS_GPIO);
		disable_irq(gps_pps_irq);
		gpio_set_value(_dio_info[bit_num].gpio, user_bit_info.value);
		enable_irq(gps_pps_irq);
	}
}


// Get the value of a DIO1 bit.
static void get_dio1_bit_value(struct bit_info *user_buf)
{
	struct bit_info 	user_bit_info;
	int					bit_num;
	int					bit_value;
	int                 gps_pps_irq;
	
	copy_from_user(&user_bit_info, user_buf, sizeof(struct bit_info));
	bit_num = user_bit_info.number;
	if ((bit_num < 0) || (bit_num >= NUM_DIO1_BITS)) {
		return;
	}
	if (_dio_info[bit_num].dir == IN) {
	    // disable the GPS_PPS interrupt since it uses gpio
	    gps_pps_irq = gpio_to_irq(PPS_GPIO);
	    disable_irq(gps_pps_irq);
		bit_value = gpio_get_value(_dio_info[bit_num].gpio);
		enable_irq(gps_pps_irq);
	} else {
		bit_value = _dio_info[bit_num].value;
	}
	put_user(bit_value, &(user_buf->value));
}



// Set the direction of a DIO1 bit.
static void set_dio1_bit_dir(struct bit_info *user_buf)
{
	struct bit_info 	user_bit_info;
	int					bit_num;
	
	printk (KERN_INFO "dio1 driver: a DIO1 bit direction was set from userland\n");
	copy_from_user(&user_bit_info, user_buf, sizeof(struct bit_info));
	bit_num = user_bit_info.number;
	if ((bit_num < 0) || (bit_num >= NUM_DIO1_BITS)) {
		return;
	}
	if (user_bit_info.dir == OUT) {
		_dio_info[bit_num].dir = OUT;
		_dio_info[bit_num].value = user_bit_info.value;
		gpio_direction_output(_dio_info[bit_num].gpio, user_bit_info.value);
	} else {
		_dio_info[bit_num].dir = IN;
		gpio_direction_input(_dio_info[bit_num].gpio);
	}
}


// Get the direction of a DIO1 bit.
static void get_dio1_bit_dir(struct bit_info *user_buf)
{
	struct bit_info 	user_bit_info;
	int					bit_num;
	
	copy_from_user(&user_bit_info, user_buf, sizeof(struct bit_info));
	bit_num = user_bit_info.number;
	if ((bit_num < 0) || (bit_num >= NUM_DIO1_BITS)) {
		return;
	}
	put_user(_dio_info[bit_num].dir, &(user_buf->dir));
}



// Provide a status string when a process
// reads from /proc/dio1
static int drvr_read_procmem(char *buf,
							 char **start,
							 off_t offset,
							 int count,
							 int *eof,
							 void *data)
{
	int	len;
		
	len = sprintf(buf, "dio1 driver is installed\n"); 	
	*eof = 1;
	return len;
}


module_init (mod_init);
module_exit (mod_exit);

MODULE_AUTHOR ("Regnad Kcin");
MODULE_LICENSE ("GPL v2");











