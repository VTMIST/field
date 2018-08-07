# Modify to the path of your cross compiler tools
CROSS_COMPILE=~/projects/tincan/buildroot-obuoy-mark2/build_arm/staging_dir/usr/bin/arm-linux-

scripts = $(wildcard *.sh)
timestamps = $(patsubst %,.%.ts,$(scripts))

flags = -mcpu=arm9 -I$(src_dir)/field/dio1		

all: sbcctl $(timestamps)

sbcctl: sbcctl.o board.o
	$(CROSS_COMPILE)gcc -mcpu=arm9 -o sbcctl sbcctl.o board.o
	cp sbcctl $(field_bin_dir)/sbcctl.exe

sbcctl.o: sbcctl.c board.h
	$(CROSS_COMPILE)gcc $(flags) -c sbcctl.c

board.o: board.c board.h $(src_dir)/field/dio1/dio1.h
	$(CROSS_COMPILE)gcc $(flags) -c board.c
	
.%.ts : %
	cp $(patsubst .%.ts,$(CURDIR)/%,$@) $(field_bin_dir) 
	touch $(CURDIR)/$@


clean:
	-rm -f $(CURDIR)/*.o
	-rm -f $(CURDIR)/sbcctl
	-rm -f $(CURDIR)/*~
	-rm -f $(timestamps)
