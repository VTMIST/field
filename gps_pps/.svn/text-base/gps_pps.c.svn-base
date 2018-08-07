/*
	GPS Pulse Per Second driver
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

#include "gps_pps.h"

#define true 1
#define false 0

typedef int boolean;

#define DEV_NAME "gps_pps"

// Pseudo PPS output polarity
#define P_PPS_ACTIVE 1
#define P_PPS_INACTIVE 0

// The ID number for the GPIO that
//  serves as the PPS interrupt input.
// It is GPIO Port F, Pin 1.
// See Documentation/gpio.txt for details.
// The bit names are defined in:
/*
~/projects/tincan/buildroot-obuoy-mark2/project_build_arm/obuoy-mark2/linux-2.6.29.6/arch/arm/mach-ep93xx/include/mach/gpio.h
*/
#define PPS_GPIO 		EP93XX_GPIO_LINE_MCCD1
#define PSEUDO_PPS_GPIO EP93XX_GPIO_LINE_EGPIO15

// Set the pseudo PPS pulse width.
// PSEUDO_PPS_HIGH_MSECS must be an integer
//	multiple of 10.
#define PSEUDO_PPS_HIGH_MSECS		100
#define PSEUDO_PPS_HIGH_JIFFIES		((PSEUDO_PPS_HIGH_MSECS * HZ) / 1000)
#define PSEUDO_PPS_LOW_JIFFIES		(HZ - PSEUDO_PPS_HIGH_JIFFIES)

static dev_t _first_dev;
static unsigned int _dev_count = 1;
static int _drvr_major_num = 100;
static int _drvr_minor_num = 0;
static struct cdev *_drvr_cdev;
static int _pps_int_installed;
static atomic_t _pps_count;
static atomic_t _pseudo_pps_count;

struct proc_status {
	struct semaphore 		lock;
	struct gps_pps_status	status;
} _proc_status;

struct timer_cntl {
	spinlock_t			lock;
	struct timer_list	timer;
	boolean				start;
	boolean				running;
	uint32_t			expires;
	boolean				gpio_allocated;
} _pseudo_pps;

struct {
	spinlock_t			lock;
	boolean				start_meas;
	boolean				measuring;
	struct drift_measurement	drift_meas;
	boolean				set_sys_time;
	struct timespec		new_sys_time;
	struct timeval 		last_pps_time;
} _dev_info;


// Function prototypes
static int install_pps_int(void);
static void uninstall_pps_int(void);
static irqreturn_t pps_isr(int irq,
					void *dev_id);
static void pseudo_pps_falling_edge(unsigned long data);
static void pseudo_pps_rising_edge(unsigned long data);
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
static void start_drift_measurement(void);
static void stop_drift_measurement(void);
static void get_drift_measurement(struct drift_measurement *user_buf);
static void set_time(struct timeval *user_sys_time_val);
static void get_time(struct timeval *user_buf);
static void start_pseudo_pps(void);
static void stop_pseudo_pps(void);
static int allocate_pseudo_pps_gpio(void);
static void free_pseudo_pps_gpio(void);
static void handle_drift_measurement(struct timeval *now);
static void force_sys_time(void);
static int jiffie_drift_adj(void);
static void set_proc_status(struct gps_pps_status *user_buf);
static int drvr_read_procmem(char *buf,
							 char **start,
							 off_t offset,
							 int count,
							 int *eof,
							 void *data);

						
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
    //printk (KERN_INFO "Opening device: %s\n", DEV_NAME);
    if (!install_pps_int())
    {
    	printk (KERN_INFO "gps_pps.drvr_open: %s: Could not install PPS ISR\n", DEV_NAME);
    	return -EIO;
    }
    if (!allocate_pseudo_pps_gpio())
    {
    	uninstall_pps_int();
    	printk (KERN_INFO "gps_pps.drvr_open: %s: Could not allocate GPIO output\n", DEV_NAME);
    	return -EIO;
    }
    if (!create_proc_read_entry(DEV_NAME, 0, NULL, drvr_read_procmem, NULL))
    {
    	uninstall_pps_int();
    	free_pseudo_pps_gpio();
    	printk (KERN_INFO "gps_pps.drvr_open: %s: create_proc_read_entry failed\n", DEV_NAME);
    	return -EIO;
    }
    return 0;
}


static int drvr_release (struct inode *inode,
						 struct file *file)
{
    //printk (KERN_INFO "Closing device: %s\n", DEV_NAME);
    stop_pseudo_pps();
    free_pseudo_pps_gpio();
    uninstall_pps_int();
    remove_proc_entry(DEV_NAME, NULL);
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
	spin_lock_init(&_pseudo_pps.lock);
	spin_lock_init(&_dev_info.lock);
	
	init_MUTEX(&(_proc_status.lock));
    _proc_status.status.time_of_last_sync = 0;
    memcpy(_proc_status.status.error, "0.0", 4);
    memcpy(_proc_status.status.latitude, "0.0", 4);
    memcpy(_proc_status.status.longitude, "0.0", 4);

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
    cdev_del (_drvr_cdev);
    unregister_chrdev_region (_first_dev, _dev_count);
    //printk (KERN_INFO "Unregistered driver %s\n",
    //        DEV_NAME);
}


// GPS pulse-per-second interrupt handler
static irqreturn_t pps_isr(int irq,
						void *dev_id)
{
	struct timeval now;
	int pps_count;
	unsigned long flags;
	
	if (_dev_info.set_sys_time)
	{
		force_sys_time();
	}	
	do_gettimeofday(&now);
	spin_lock_irqsave(&_dev_info.lock, flags);
	_dev_info.last_pps_time = now;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
	
	if (_dev_info.measuring)
	{
		handle_drift_measurement(&now);
	}
	atomic_inc(&_pps_count);
	if (_pseudo_pps.start)
	{
		_pseudo_pps.start = false;
		stop_pseudo_pps();
		start_pseudo_pps();
	}
	pps_count = atomic_read(&_pps_count);
	if ((pps_count % (60 * 15)) == 0)
	{
		//printk(KERN_INFO "gps_pps: pseudo_pps_count = %d, pps_count = %d, sys_time = %d\n",
		//				atomic_read(&_pseudo_pps_count), pps_count, (int)(now.tv_sec));
	}
	//printk(KERN_INFO "PPS at %d s, %d usec\n", tv.tv_sec, tv.tv_usec);
	return IRQ_HANDLED;
}


// Force the system time to _dev_info.new_sys_time
static void force_sys_time(void)
{
	unsigned long flags;
	struct timespec new_time;
	
	spin_lock_irqsave(&_dev_info.lock, flags);
	new_time = _dev_info.new_sys_time;
	_dev_info.set_sys_time = false;
	do_settimeofday(&new_time);
	spin_unlock_irqrestore(&_dev_info.lock, flags);
}


static void handle_drift_measurement(struct timeval *now)
{
	unsigned long flags;
	
	spin_lock_irqsave(&_dev_info.lock, flags);
	if (_dev_info.start_meas)
	{
		_dev_info.drift_meas.begin_sys_time = *now;
		_dev_info.start_meas = false;
	}
	else
	{
		++_dev_info.drift_meas.gps_seconds;
	}
	_dev_info.drift_meas.end_sys_time = *now;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
}


static void start_pseudo_pps(void)
{
	unsigned long flags;
	
	spin_lock_irqsave(&_pseudo_pps.lock, flags);	
	init_timer(&_pseudo_pps.timer);
	_pseudo_pps.expires = jiffies + PSEUDO_PPS_HIGH_JIFFIES + 1;
	_pseudo_pps.timer.expires = _pseudo_pps.expires;
	_pseudo_pps.timer.function = pseudo_pps_falling_edge;		
	add_timer(&_pseudo_pps.timer);
	gpio_set_value(PSEUDO_PPS_GPIO, P_PPS_ACTIVE);
	_pseudo_pps.running = true;
	atomic_set(&_pps_count, 0);
	atomic_set(&_pseudo_pps_count, 0);
	spin_unlock_irqrestore(&_pseudo_pps.lock, flags);
}


static void stop_pseudo_pps(void)
{
	unsigned long flags;
	
	spin_lock_irqsave(&_pseudo_pps.lock, flags);
	if (_pseudo_pps.running)
	{
		_pseudo_pps.running = false;
		del_timer_sync(&_pseudo_pps.timer);
	}
	gpio_set_value(PSEUDO_PPS_GPIO, P_PPS_INACTIVE);
	spin_unlock_irqrestore(&_pseudo_pps.lock, flags);
}


// Called when the pseudo PPS timer expires
//  for the falling edge of the pseudo PPS pulse
static void pseudo_pps_falling_edge(unsigned long data)
{
	unsigned long flags;
	
	spin_lock_irqsave(&_pseudo_pps.lock, flags);
	if (_pseudo_pps.running)
	{
		init_timer(&_pseudo_pps.timer);
		_pseudo_pps.expires += PSEUDO_PPS_LOW_JIFFIES;
		_pseudo_pps.timer.expires = _pseudo_pps.expires;
		_pseudo_pps.timer.function = pseudo_pps_rising_edge;		
		add_timer(&_pseudo_pps.timer);
		gpio_set_value(PSEUDO_PPS_GPIO, P_PPS_INACTIVE);
	}
	spin_unlock_irqrestore(&_pseudo_pps.lock, flags);
}


// Called when the pseudo PPS timer expires
//  for the rising edge of the pseudo PPS pulse.
static void pseudo_pps_rising_edge(unsigned long data)
{
/*
	** Note about periodic jumps in P-PPS pulse rising edge **
	If you look at the PPS and the P-PPS pulses on a scope,
	triggering on the rising edge of PPS, you will notice
	that periodically a P-PPS leading edge will be delayed
	by 10 msec.  The next P-PPS pulse will be fine.
	This is caused because jiffie_drift_adj() uses the time
	of day to keep P-PPS locked to the change of second.
	The time of day is is adjusted by the kernel to
	compensate for drift and error.  Periodically the time of
	day jumps relative to jiffies.  This causes the one P-PPS
	timing jump.  Nothing (that I know of) can be done to get
	rid of the periodic jump.
*/
	unsigned long flags;
	
	int drift_adj = jiffie_drift_adj();
	spin_lock_irqsave(&_pseudo_pps.lock, flags);	
	if (_pseudo_pps.running)
	{
		init_timer(&_pseudo_pps.timer);
		_pseudo_pps.expires += PSEUDO_PPS_HIGH_JIFFIES + drift_adj;
		_pseudo_pps.timer.expires = _pseudo_pps.expires;
		_pseudo_pps.timer.function = pseudo_pps_falling_edge;		
		add_timer(&_pseudo_pps.timer);
		gpio_set_value(PSEUDO_PPS_GPIO, P_PPS_ACTIVE);
	}
	spin_unlock_irqrestore(&_pseudo_pps.lock, flags);
	atomic_inc(&_pseudo_pps_count);
}


// ** Control P-PPS/System Clock Skew **
// gps_mgr uses adjtimex to compensate
// for system clock drift and error.  This
// keeps the system time synced to UTC.  P-PPS
// timing is based on jiffies which are not
// affected by the adjtimex compensation.
// So, P-PPS drifts against system clock time.
// Return the number of jiffies required to
// nudge the P-PPS rising pulse closer to
// system time.
// Return +1, -1, or 0 jiffies
static int jiffie_drift_adj(void)
{
	const int usec_per_jiffie = 1000000/HZ;
	const int hysteresis_usec = 500;	
	const int thresh = usec_per_jiffie/2 + hysteresis_usec;
	const int slow_thresh = thresh;
	const int fast_thresh = 1000000 - thresh;
	const int middle = 1000000/2;
	struct timeval now;
	
	do_gettimeofday(&now);
	if (now.tv_usec > fast_thresh) return 0;
	if (now.tv_usec < slow_thresh) return 0;
	if (now.tv_usec < middle) return -1;
	return 1;
}


// Reserve the GPIO pin used for pseudo PPS output
static int allocate_pseudo_pps_gpio(void)
{
	int result;
	
	_pseudo_pps.gpio_allocated = false;
	if (!gpio_is_valid(PSEUDO_PPS_GPIO))
	{
		printk(KERN_INFO "gps_pps.allocate_pseudo_pps_gpio: gpio_is_valid failed\n");
		return false;
	}
	if ((result = gpio_request(PSEUDO_PPS_GPIO, DEV_NAME)) != 0)
	{
		printk(KERN_INFO "gps_pps.allocate_pseudo_pps_gpio: gpio_request failed %d\n", result);
		return false;
	}
	if ((result = gpio_direction_output(PSEUDO_PPS_GPIO, 0)) != 0)
	{
		gpio_free(PSEUDO_PPS_GPIO);
		printk(KERN_INFO "gps_pps.allocate_pseudo_pps_gpio: gpio_direction_input failed %d\n", result);
		return false;
	}
	_pseudo_pps.gpio_allocated = true;
	return true;
}


static void free_pseudo_pps_gpio(void)
{
	if (_pseudo_pps.gpio_allocated)
	{
		gpio_free(PSEUDO_PPS_GPIO);
		_pseudo_pps.gpio_allocated = false;
	}
}


// Install GPS pulse-per-second interrupt.
// Return true for success, false for failure.
static int install_pps_int(void)
{
	int result;
	int pps_irq;
	
	if (!gpio_is_valid(PPS_GPIO))
	{
		printk(KERN_INFO "gps_pps.install_pps_isr: gpio_is_valid failed\n");
		return false;
	}
	if ((result = gpio_request(PPS_GPIO, DEV_NAME)) != 0)
	{
		printk(KERN_INFO "gps_pps.install_pps_isr: gpio_request failed %d\n", result);
		return false;
	}
	if ((result = gpio_direction_input(PPS_GPIO)) != 0)
	{
		gpio_free(PPS_GPIO);
		printk(KERN_INFO "gps_pps.install_pps_isr: gpio_direction_input failed %d\n", result);
		return false;
	}
	result = gpio_to_irq(PPS_GPIO);
	if (result < 0)
	{
		gpio_free(PPS_GPIO);
		printk(KERN_INFO "gps_pps.install_pps_isr: gpio_to_irq failed %d\n", result);
		return false;
	}
	pps_irq = result;	
	result = request_irq(pps_irq,
						pps_isr,
						IRQF_TRIGGER_RISING,
						DEV_NAME,
						NULL);
	if (result != 0)
	{
		gpio_free(PPS_GPIO);
		printk(KERN_INFO "gps_pps.install_pps_isr: request_irq failed, returned %d\n", result);
		return false;
	}
	_pps_int_installed = true;
	return true;
}


// Uninstall the GPS pulse-per-second interrupt
// service handler.
static void uninstall_pps_int(void)
{
	if (_pps_int_installed)
	{
		gpio_free(PPS_GPIO);
		free_irq(gpio_to_irq(PPS_GPIO), NULL);
		_pps_int_installed = false;
	}	
}


static int drvr_ioctl (struct inode *inode,
						struct file *file,
						unsigned int cmd,
						unsigned long arg)
{
	int err = 0;
	unsigned long flags;
	
    //printk (KERN_INFO "IOCTL cmd received: %s:\n", DEV_NAME);
    if (_IOC_TYPE(cmd) != GPS_PPS_IOC_MAGIC) return ENOTTY;
    if (_IOC_NR(cmd) > GPS_PPS_IOC_MAX_NR) return ENOTTY;
    
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
    	case GPS_PPS_IOC_SET_TIME:
    		set_time((struct timeval *) arg);
    		break;
    	case GPS_PPS_IOC_GET_TIME:
    		get_time((struct timeval *) arg);
    		break;
    	case GPS_PPS_IOC_START_DRIFT:
    		start_drift_measurement();
    		break;
    	case GPS_PPS_IOC_STOP_DRIFT:
    		stop_drift_measurement();
    		break;
    	case GPS_PPS_IOC_GET_DRIFT:
    		get_drift_measurement((struct drift_measurement *) arg);
    		break;
    	case GPS_PPS_IOC_START_PSEUDO_PPS:
			spin_lock_irqsave(&_dev_info.lock, flags);	// disables interrupts
			_pseudo_pps.start = true;
			spin_unlock_irqrestore(&_dev_info.lock, flags);
    		break;
    	case GPS_PPS_IOC_SET_PROC_STATUS:
    		set_proc_status((struct gps_pps_status *) arg);
    		break;
    	default:
    		return -EFAULT;
    }   
	return 0;
}


// Set the system time when the next PPS
//  is detected.  Fractional seconds is always
//  set to zero since the system time is always
//  set when the PPS interrupt occurs.
static void set_time(struct timeval *user_sys_time_val)
{
	unsigned long flags;
	struct timeval val;
	struct timespec spec;
	
	copy_from_user(&val, user_sys_time_val, sizeof(struct timeval));
	spec.tv_sec = val.tv_sec;
	spec.tv_nsec = 0;
	
	spin_lock_irqsave(&_dev_info.lock, flags);	// disables interrupts
	_dev_info.new_sys_time = spec;
	_dev_info.set_sys_time = true;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
}


// Return the system time of the most recent
// PPS interrupt
static void get_time(struct timeval *user_buf)
{
	unsigned long flags;
	struct timeval last_pps_time;
	
	spin_lock_irqsave(&_dev_info.lock, flags);
	last_pps_time = _dev_info.last_pps_time;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
	copy_to_user(user_buf, &last_pps_time, sizeof(struct timeval));
}


// Start a system clock drift measurement
static void start_drift_measurement()
{
	unsigned long flags;
	
	spin_lock_irqsave(&_dev_info.lock, flags);	// disables interrupts
	_dev_info.drift_meas.gps_seconds = 0;
	_dev_info.start_meas = true;
	_dev_info.measuring = true;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
}


// Stop a system clock drift measurement
static void stop_drift_measurement()
{
	unsigned long flags;
	
	spin_lock_irqsave(&_dev_info.lock, flags);	// disables interrupts
	_dev_info.measuring = false;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
}


// Copy the most recent sys clock drift measurement
//  to a user buffer
static void get_drift_measurement(struct drift_measurement *user_buf)
{
	unsigned long flags;
	struct drift_measurement drift_meas;
	
	spin_lock_irqsave(&_dev_info.lock, flags);	// disables interrupts
	drift_meas = _dev_info.drift_meas;
	spin_unlock_irqrestore(&_dev_info.lock, flags);
	copy_to_user(user_buf, &drift_meas, sizeof(struct drift_measurement));
}


// Set the /dev/gps_pps status.
// The status is accessible to any process
// by reading from /proc/gps_pps
static void set_proc_status(struct gps_pps_status *user_buf)
{
	if (sizeof(struct gps_pps_status) > PAGE_SIZE)
	{
		printk("gps_pps.set_proc_status: can't set status string, struct gps_pps_status > PAGE_SIZE\n");
		return;
	}
	down(&(_proc_status.lock));
	copy_from_user(&(_proc_status.status), user_buf, sizeof(struct gps_pps_status));	
	up(&(_proc_status.lock));
}


// Provide a status string when a process
// reads from /proc/gps_pps
static int drvr_read_procmem(char *buf,
							 char **start,
							 off_t offset,
							 int count,
							 int *eof,
							 void *data)
{
	// Note: floating point values are stored in
	//	string form since the kernel sprintf doesn't
	//	support floating point conversion.

	int	len;
	struct timeval now;
	int sync_age;
		
	do_gettimeofday(&now);
	down(&(_proc_status.lock));
	sync_age = now.tv_sec - _proc_status.status.time_of_last_sync;
	len = sprintf(buf, "Sync Age,Sys Time Error,Lat,Long\n%d,%s,%s,%s\n",
						sync_age,
						_proc_status.status.error,
						_proc_status.status.latitude,
						_proc_status.status.longitude); 	
	up(&(_proc_status.lock));
	*eof = 1;
	return len;
}


module_init (mod_init);
module_exit (mod_exit);

MODULE_AUTHOR ("Regnad Kcin");
MODULE_LICENSE ("GPL v2");











