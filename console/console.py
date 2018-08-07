#! /usr/bin/python

# AAL-PIP Console Program
# Allows user to connect to other processes,
#  send XMLRPC commands and view process
#  console output.

import sys

import threading
import readline
import xmlrpclib

import utils
import sock_utils
import logs
import global_config
import console_config
import svr_proxy_config
import modem_svr_config
import usb_mgr_config
import fg_mgr_config
import sc_mgr_config
import cases_mgr_config


def out(s, log):
    """Print and log s"""
    print s
    #log.info(s)
    
    
class ReceiveProcOutput(threading.Thread):
    """ Display console output from connected process """
    def __init__(self,
                proc_info,
                log):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._proc_info = proc_info
        self._log = log
        self._stop_event = threading.Event()
        self.name = 'ReceiveProcOutput thread'
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        while not self._stop_event.isSet():
            if not self._proc_info.sock_h.is_running():
                break
            s = utils.q_get(self._proc_info.sock_h.get_read_q(),
                            get_timeout=0.5)
            if s:
                print s,
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        self._log.debug('Exiting %s ' % self.name)
        
    def is_running(self):
        return self._running
        
    def stop(self):
        if self._running:
            self._stop_event.set()
            self.join()


def send_xmlrpc_cmd(cmd_fields, proc_info):
    """ Send an XMLRPC command to the connected process """
    if not (proc_info.sock_h and proc_info.sock_h.is_running()):
        out('No connected process.  Cannot send XMLRPC command.', log)
        return       
    if cmd_fields[0] == 'execute_sys_cmd':
        cmd = 'xmlrpc_svr.%s("' % cmd_fields[0]
        sys_cmd = ' '.join(cmd_fields[1:])
        cmd = ''.join([cmd, sys_cmd, '")'])
    else:    
        cmd = 'xmlrpc_svr.%s(' % cmd_fields[0]
        for arg in cmd_fields[1:]:
            cmd = ''.join((cmd, "'", arg, "', "))
        cmd = cmd + ')'
        if cmd.endswith(', )'):
            cmd = cmd.replace(', )', ')')              
    out('Sending XMLRPC command: %s' % cmd, log)
    try:
        xmlrpc_svr = xmlrpclib.Server(proc_info.xmlrpc_url, allow_none=True)
        result = eval(cmd)
    except Exception, msg:
        out('XMLRPC command exception:  %s' % msg, log)
        return
    #out(result, log)
    #if result != 'OK':
    #    out('XMLRPC command failed.  See process log file for details.', log)
    #out('result = %s' % result, log)
    
        
def disconnect_from_proc(proc_info):
    """Disconnect from a process"""
    if proc_info.sock_h:
        proc_info.sock_h.stop()
    proc_info.sock_h = None


def process_xmlrpc_cmd(raw_cmd, proc_info, log):
    """Process an xmlrpc command entered by the user"""
    raw_cmd = raw_cmd.lower()
    #out('\nraw_cmd is %s ' % utils.bytes_to_hex(raw_cmd), log)
    fields = raw_cmd.split(' ')
    if len(fields) == 0:
        return
    if fields[0] == '':
        return
    if fields[0].startswith('dis'):
        disconnect_proc(proc_info)
        return
    if proc_info.sock_h:
        # Connected to another process, send XMLRPC command
        send_xmlrpc_cmd(fields, proc_info)
        return
        
        
def run_proc_connection(proc_info, log):
    """Prompt the user for an xmlprc command and process it"""
    proc_output_thread = ReceiveProcOutput(proc_info, log)                
    while True:
        if not proc_info.sock_h.is_running():
            break
        try:
            raw_cmd = raw_input(proc_info.prompt)
        except Exception:
            disconnect_from_proc(proc_info)
            proc_output_thread.stop()
            raise
        log.info(''.join((proc_info.prompt, raw_cmd)))
        if raw_cmd.lower().startswith('dis'):
            break
        process_xmlrpc_cmd(raw_cmd, proc_info, log)
    disconnect_from_proc(proc_info)
    proc_output_thread.stop()
    
        
#================================================================

def expand_proc_mne(proc_mne):
    """Expand a process nmemonic into console_port, exe_file_name, xml_rpc_url"""
    return console_config.proc_mne_params.get(proc_mne, [None, None, None])
    

def connect_to_proc(proc_mne, log):
    """ Connect to a process """
    null_cons_info = utils.Bunch(sock_h=None, exe_file=None, xmlrpc_url=None, prompt=None)     
    cons_port, exe_file, xmlrpc_url = expand_proc_mne(proc_mne)
    if cons_port is None:
        return null_cons_info
    #print 'cons_port is %d' % cons_port
    sock_h = sock_utils.connect_to_server(log, 'localhost', cons_port)
    if sock_h is None:
        print 'sock_h was None'
        return null_cons_info
    prompt = ''.join([proc_mne, ' > '])
    return utils.Bunch(sock_h=sock_h, exe_file=exe_file, xmlrpc_url=xmlrpc_url, prompt=prompt)
    
    
def exec_connect_cmd(cmd_fields, log):
    """Execute the connect command"""
    if len(cmd_fields) < 2:
        print 'Connect to what?'
        return
    proc_nme = cmd_fields[1]
    proc_info = connect_to_proc(proc_nme, log)
    if proc_info.sock_h:
        out('Connected to %s' % proc_nme, log)
        run_proc_connection(proc_info, log)
    else:
        out('Could not connect to %s' % proc_nme, log)
        

def exec_help(log):
    """ Display help info """
    help_str = ''.join(('AAL-PIP Console Commands\n',
    '> con <process_mnemonic>\n',    
    '       Connect to a process console\n',   
    '           Process mnemonics:\n',    
    '               cases     = CASES GPS receiver manager\n',    
    '               fg        = flux gate magnetometer manager\n',    
    '               hw        = hardware manager\n',
    '               modem_svr = Iridium modem server\n',
    '               sc        = search coil magnetometer manager\n',    
    '               svr_proxy = internet server proxy\n',    
    '               super     = AAL-PIP supervisor\n',    
    '               usb       = USB flash storage manager\n',
    '> dis\n',    
    '       Disconnect from a process console\n',   
    '> quit\n',    
    '       Quit the AAL-PIP console application\n'   
    ))
    out(help_str, log)
    
    
def process_console_cmd(raw_cmd, log):
    """Process a console command"""
    raw_cmd = raw_cmd.lower()
    #out('\nraw_cmd is %s ' % utils.bytes_to_hex(raw_cmd), log)
    fields = raw_cmd.split(' ')
    if len(fields) == 0:
        return
    if fields[0] == '':
        return
    if fields[0].startswith('con'):
        exec_connect_cmd(fields, log)
    elif fields[0].startswith('help'):
        exec_help(log)
    else:
        out('Unknown command: %s' % raw_cmd, log)
        

def _run_console(log):
    """Prompt the user for a console command, process it"""
    prompt = 'console > '
    while True:
        try:
            raw_cmd = raw_input(prompt)
        except Exception:
            raise
        log.info(''.join((prompt, raw_cmd)))
        if raw_cmd.lower().startswith('quit'):
            break
        if raw_cmd.lower().startswith('exit'):
            break
        process_console_cmd(raw_cmd, log)
                

if __name__ == '__main__':
    print('Starting console')
    log = logs.open(console_config.log_name,
                    console_config.log_dir,
                    console_config.log_level,
                    file_max_bytes = console_config.log_file_max_bytes,
                    num_backup_files = console_config.log_files_backup_files)
    log.info('****** Starting AAL-PIP console ******')
    out('', log)
    out('****************************************', log)
    out('***      AAL-PIP System Console      ***', log)
    out('***        Enter \'help\' for a        ***', log)
    out('***         list of commands         ***', log)
    out('****************************************', log)
    out('AAL-PIP software version %s' % global_config.sw_version_number, log)
    out('', log)
    try:
        _run_console(log)
    except KeyboardInterrupt:
        msg = 'KeyboardInterrupt (exiting)'
        out(msg, log)
    except Exception:
        # handle all unexpected application exceptions
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
         
    log.info('****** Exiting AAL-PIP console ******')
    utils.wait_for_child_threads()
    
    
