
# Disable all the default suffix rules
.SUFFIXES:

CROSS_COMPILE=~/projects/tincan/buildroot-obuoy-mark2/build_arm/staging_dir/usr/bin/arm-linux-
# TBD move CROSS_COMPILE up in the Makefile hierarchy

srcs := gps_mgr.c \
		gps_io_thread.c	\
		logging.c
			
hdrs := gps_io_thread.h \
		logging.h \
		includes.h \
		$(src_dir)/field/gps_pps/gps_pps.h
		
objs := gps_mgr.o \
		gps_io_thread.o \
		logging.o
		
flags = -mcpu=arm9 -Wall -Wstrict-prototypes -I$(src_dir)/field/gps_pps		
libs = -lpthread

gps_mgr : $(objs)
	$(CROSS_COMPILE)gcc -o $@ $(flags) $(objs) $(libs)
	cp $@ $(field_bin_dir)/$@.exe
	
gps_io_thread.o : gps_io_thread.c $(hdrs)
gps_mgr.o : gps_mgr.c $(hdrs)
logging.o : logging.c logging.h includes.h

$(hdrs) :
	
%.o : %.c
	$(CROSS_COMPILE)gcc -c $(flags) $< -o $@
	
clean:
	rm -f $(CURDIR)/*.o
	rm -f $(CURDIR)/gps_mgr
	rm -f $(CURDIR)/*~
	rm -f .*.ts
