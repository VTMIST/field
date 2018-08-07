
targ = gps_pps
scripts = $(wildcard *.sh)
timestamps = $(patsubst %,.%.ts,$(scripts))

obj-m += $(targ).o

KDIR := ~/projects/tincan/buildroot-obuoy-mark2/project_build_arm/obuoy-mark2/linux-2.6.29.6
PWD := $(shell pwd)
LINUX26_MAKE_FLAGS = HOSTCC="/usr/bin/gcc" HOSTCFLAGS="" ARCH=arm INSTALL_MOD_PATH=~/projects/tincan/buildroot-obuoy-mark2/project_build_arm/obuoy-mark2/root CROSS_COMPILE=~/projects/tincan/buildroot-obuoy-mark2/build_arm/staging_dir/usr/bin/arm-linux-uclibcgnueabi- LDFLAGS="-L~/projects/tincan/buildroot-obuoy-mark2/build_arm/staging_dir/lib -L~/projects/tincan/buildroot-obuoy-mark2/build_arm/staging_dir/usr/lib --sysroot=~/projects/tincan/buildroot-obuoy-mark2/build_arm/staging_dir/" LZMA="~/projects/tincan/buildroot-obuoy-mark2/toolchain_build_arm/bin/lzma" PATH=:/usr/lib/qt-3.3/bin:/usr/kerberos/bin:/usr/local/bin:/usr/bin:/bin:/usr/X11R6/bin:~/SE2009/se_14000202_linux_full/yes/bin/:~/bin:~/SE2009/se_14000202_linux_full/yes/bin/

all: gps_pps.ko $(timestamps)

$(targ).ko : $(targ).c $(targ).mod.c $(targ).h
	$(MAKE) $(LINUX26_MAKE_FLAGS) -C $(KDIR) SUBDIRS=$(PWD)
	cp $(targ).ko $(field_bin_dir)
	
.%.ts : %
	cp $(patsubst .%.ts,$(CURDIR)/%,$@) $(field_bin_dir) 
	touch $(CURDIR)/$@

clean:
	-rm -f *.o
	-rm -f *.ko
	-rm -f .*.cmd
	-rm -f modules.order
	-rm -f Module.symvers
	-rm -f .tmp_versions/*
	-rmdir .tmp_versions
	-rm -f *~
	-rm -f .*.ts
