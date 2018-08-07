# Disable all the default suffix rules
.SUFFIXES:

# Run make recursively on all subdirectories
.PHONY : all
all :
	@$(MAKE) -C console
	@$(MAKE) -C fg_mgr
	@$(MAKE) -C gps_mgr
	@$(MAKE) -C gps_pps
	@$(MAKE) -C modem
	@$(MAKE) -C modem_svr
	@$(MAKE) -C sbcctl
	@$(MAKE) -C sc_mgr
	@$(MAKE) -C svr_proxy
	@$(MAKE) -C usb_mgr
	@$(MAKE) -C dio1
	@$(MAKE) -C updater	
	@$(MAKE) -C cases_mgr	
	@$(MAKE) -C start_stop	
	@$(MAKE) -C hw_mgr	
	@$(MAKE) -C super
	@$(MAKE) -C utils
	@$(MAKE) -C watchdogs
	@$(MAKE) -C hf_mgr
	@$(MAKE) -C file_svr
	@$(MAKE) -C cpu_load_wd

clean :
	@$(MAKE) clean -C console
	@$(MAKE) clean -C fg_mgr
	@$(MAKE) clean -C gps_mgr
	@$(MAKE) clean -C gps_pps
	@$(MAKE) clean -C modem
	@$(MAKE) clean -C modem_svr
	@$(MAKE) clean -C sbcctl
	@$(MAKE) clean -C sc_mgr
	@$(MAKE) clean -C svr_proxy
	@$(MAKE) clean -C usb_mgr
	@$(MAKE) clean -C dio1
	@$(MAKE) clean -C updater
	@$(MAKE) clean -C cases_mgr
	@$(MAKE) clean -C start_stop
	@$(MAKE) clean -C hw_mgr			
	@$(MAKE) clean -C super			
	@$(MAKE) clean -C utils			
	@$(MAKE) clean -C watchdogs			
	@$(MAKE) clean -C hf_mgr			
	@$(MAKE) clean -C file_svr
	@$(MAKE) clean -C cpu_load_wd			
	rm -f *~
