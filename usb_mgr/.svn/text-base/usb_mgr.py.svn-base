#! /usr/bin/python

# USB Manager Process

import sys
import threading
import Queue
import gzip
import time
import xmlrpclib

import utils
import sock_utils
import logs
import hw_mgr_config
import usb_mgr_config
import global_config
from BasicXMLRPCThread import BasicXMLRPCThread
from SockConsole import SockConsole

        
class JobInfo:
    def __init__(self,
            src_file_name,
            process_mne,
            tmp_path,
            compress):
        self.src_file_name = src_file_name
        self.process_mne = process_mne
        self.tmp_path = tmp_path
        self.compress = compress
        

class Dispatcher(threading.Thread):
    """Queue and run StoreFile jobs sequentially"""
    def __init__(self, log, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._exit_callback = exit_callback
        self._job_queue = Queue.Queue()
        self._stop_event = threading.Event()
        self.name = 'Dispatcher'
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
        job_info = None
        
        while not self._stop_event.isSet():
            job_info = utils.q_get(self._job_queue, get_timeout=0.5)
            if job_info:
                self._execute_job(job_info)
                
        # Execute remaining jobs
        while True:
            job_info = utils.q_get(self._job_queue, get_timeout=0.5)
            if job_info:
                self._execute_job(job_info)
            else:
                break
        utils.wait(5)
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
        
    def _execute_job(self, job_info):
        if self._mount_drive():
            job = StoreFileJob(job_info.src_file_name,
                                job_info.process_mne,
                                job_info.tmp_path,
                                job_info.compress,
                                self._log)
            while job.is_running():
                utils.wait(0.25)   
        else:                                
            self._log.error('Write failed.  USB flash drive is not mounted.')
            # Delete the temp file.  StoreFileJob usually does it.
            utils.delete_file(job_info.tmp_path, self._log)
        
    def create_store_file_job(self,
                                src_file_name,
                                process_mne,
                                tmp_path,
                                compress):
        """Queue information for a store_file job to be run later"""
        self._job_queue.put(JobInfo(src_file_name,
                                    process_mne,
                                    tmp_path,
                                    compress))
                        
    def _mount_drive(self):
        """If not already mounted, mount the USB flash drive.
        Return False if failed.
        """
        # If the /mnt/usbflash/data dir does not exist,
        #   try to mount sda1, sdb1 or sdc1.  The flash drive
        #   could be on any of those devices.
        
        if utils.path_exists(usb_mgr_config.usb_flash_data_dir):
            return True
        dev_a = usb_mgr_config.usb_flash_device_a
        dev_b = usb_mgr_config.usb_flash_device_b
        dev_c = usb_mgr_config.usb_flash_device_c
        mount_pt = usb_mgr_config.usb_flash_dir
        utils.call_subprocess('umount %s' % mount_pt)        
        utils.call_subprocess('mount %s %s' % (dev_a, mount_pt))
        if utils.path_exists(usb_mgr_config.usb_flash_data_dir):
            self._log.info('Mounted USB device %s' % dev_a) 
            return True
        utils.call_subprocess('mount %s %s' % (dev_b, mount_pt))
        if utils.path_exists(usb_mgr_config.usb_flash_data_dir):
            self._log.info('Mounted USB device %s' % dev_b) 
            return True
        utils.call_subprocess('mount %s %s' % (dev_c, mount_pt))
        if utils.path_exists(usb_mgr_config.usb_flash_data_dir):
            self._log.info('Mounted USB device %s' % dev_c) 
            return True
        return False        
                                            
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
            
            
class StoreFileJob(threading.Thread):
    """ Store a file on the USB flash drive.
        Delete the source file when completed.
    """
    def __init__(self,
                dest_file_name,
                process_mne,
                src_path,
                compress,
                log,
                exit_callback=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._dest_file_name = dest_file_name
        self._process_mne = process_mne
        self._src_path = src_path
        self._compress = compress
        self._log = log
        self._exit_callback = exit_callback
        self.name = 'StoreFileJob'
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        self._running = True
        self._started = True
        self._log.debug('Starting %s ' % self.name)
        
        while True:
            # Assume USB flash drive is powered up and mounted.
            # If necessary, create the USB flash destination dir.
            dest_dir = self._get_dest_dir(self._dest_file_name)
            utils.make_dirs(dest_dir, self._log)
            comp_ratio = 1.0
            if self._compress:
                compressed_path = self._src_path + '.gz'
                if not self._compress_file(self._src_path, compressed_path):
                    self._log.error('Error: file compression failed on %s' % \
                                        self._src_path)
                    utils.delete_file(self._src_path, self._log)
                    utils.delete_file(compressed_path, self._log)
                    return False
                orig_bytes = float(utils.get_file_size(self._src_path))
                comp_bytes = float(utils.get_file_size(compressed_path))
                comp_ratio = orig_bytes/comp_bytes
                from_path = compressed_path
                to_path = ''.join((dest_dir, '/', self._dest_file_name, '.gz'))
            else:
                from_path = self._src_path
                to_path = ''.join((dest_dir, '/', self._dest_file_name))
            self._log.info('Storing %s' % to_path)
            self._log.info('  Compression ratio was %.2f to 1' % comp_ratio)
            try:
                utils.copy_file(from_path, to_path, self._log)
            except Exception:
                self._log.info('Error: write to %s failed' % to_path)
            # Delete the temp files
            try:
                utils.delete_file(self._src_path, self._log)
            except Exception:
                self._log.info('Error: could not delete %s' % self._src_path)
            if self._compress:
                try:
                    utils.delete_file(compressed_path, self._log)
                except Exception:
                    self._log.error('Could not delete %s' % compressed_path)
            break
            
        self._running = False
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
    
    def _get_dest_dir(self, dest_file_name):
        """ Return a directory that has the form:
            /mnt/usbflash/data/fg/2011_03_09/
        """
        if dest_file_name.startswith('fg'):
            return ''.join([usb_mgr_config.usb_flash_data_dir,
                                '/fg/', dest_file_name[3:13]])                                
        elif dest_file_name.startswith('sc'):
            return ''.join([usb_mgr_config.usb_flash_data_dir,
                                '/sc/', dest_file_name[3:13]])                                
        elif dest_file_name.startswith('cases'):
            return ''.join([usb_mgr_config.usb_flash_data_dir,
                                '/cases/', dest_file_name[6:16]])                                
        elif dest_file_name.startswith('hskp'):
            return ''.join([usb_mgr_config.usb_flash_data_dir,
                                '/hskp/', dest_file_name[5:15]])                                
        elif dest_file_name.startswith('hf'):
            return ''.join([usb_mgr_config.usb_flash_data_dir,
                                '/hf/', dest_file_name[3:13]])                                
        else:
            self._log.error('StoreFileJob._get_dest_dir: Unknown data file prefix')
            return None
        
    def is_running(self):
        return self._running
        
    def _compress_file(self, src_path, dest_path):
        """ Compress a file
            Return True if successful
        """
        msg = 'Compressing %s to %s' % (src_path, dest_path)
        self._log.debug(msg)
        try:
            input = open(src_path, 'rb')
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
            return False
        try:
            output = gzip.open(dest_path, 'wb', compresslevel=9)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
            return False        
        while True:
            try:
                chunk = input.read(1024)
                if not chunk:
                    break
                output.write(chunk)
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
                output.close()
                return False
        try:
            output.close()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
            return False
        return True        
        
    
    
class XMLRPCThread(BasicXMLRPCThread):
    """An extended BasicXMLRPCThread"""
    def __init__(self, host, port, console, dispatcher, log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._console = console
        self._dispatcher = dispatcher
        self._log = log
        self._server.register_function(self.help)
        self._server.register_function(self.store_file)
        self._server.register_function(self.mount_usb_flash)
        self._server.register_function(self.unmount_usb_flash)
        
    def help(self):
        """ Show the available XMLRPC commands """
        msg = ''.join(( \
            'USB Manager XMLRPC Commands\n',
            '> help\n',
            '       Print this list of XMLRPC commands\n'       
            '> store_file <proc_mne> <file_name>\n',
            '       Store a file on the USB flash drive\n',
            '           proc_mne:\n',
            '               mnemonic of the process that created the file\n',
            '           file_name:\n',
            '               the full path of the file to be stored\n',
            '> mount_usb_flash\n',
            '       Mount the USB flash drive and keep it mounted\n'       
            '> unmount_usb_flash\n',
            '       Allow the USB manager to unmount the USB drive\n'       
        ))
        self._console.write(msg)
        return 'OK'

    def store_file(self, process_mne, src_path, compress=True):
        """ Store a file on the USB flash drive """
        self._log.debug('XMLRPC: got store_file command')        
        # Copy the source file to a temp file
        tmp_path = usb_mgr_config.temp_dir + utils.temp_filename()
        if not utils.copy_file(src_path, tmp_path, self._log):
            self._console.write('\n' + 'Failed.  See usb_mgr.log for details.')
            return 'Failed'
        # Queue up a job to be completed later
        src_file_name = utils.get_path_basename(src_path)
        self._dispatcher.create_store_file_job(src_file_name,
                                                process_mne,
                                                tmp_path,
                                                compress)
        return 'OK'
        
    def mount_usb_flash(self):
        """Mount the USB flash drive and keep it mounted.
        Prevent the store_file command from unmounting the drive.
        """
        self._dispatcher.set_unmount_allowed(False)
        return 'OK'
        
    def unmount_usb_flash(self):
        """Allow the dispatcher to unmount the USB flash drive"""
        self._dispatcher.set_unmount_allowed(True)
        return 'OK'

    
def _run_mgr(log):
    """
        Run the instrument manager until terminated
        via XMLRPC command
    """
    log.info('')
    log.info('****** Starting USB manager ******')
    
    try:
        console = SockConsole('localhost',
                            usb_mgr_config.console_port,
                            log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
    try:
        dispatcher = Dispatcher(log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                            usb_mgr_config.XMLRPC_port, console, dispatcher, log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    while True:
        try:
            utils.wait(0.5)
            if not console.is_running():
                log.error('Console thread died unexpectedly')
                break
            if not xmlrpc_thread.is_running():
                log.error('XMLRPC server thread died unexpectedly')
                break
            if not dispatcher.is_running():
                log.error('Dispatcher thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if usb_mgr_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT (ignored)')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
                   
    xmlrpc_thread.stop()
    dispatcher.stop()
    console.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting USB manager ******')
    
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if usb_mgr_config.daemonize:
        utils.daemonize()
    log = logs.open(usb_mgr_config.log_name,
                    usb_mgr_config.log_dir,
                    usb_mgr_config.log_level,
                    file_max_bytes = usb_mgr_config.log_file_max_bytes,
                    num_backup_files = usb_mgr_config.log_files_backup_files)
    utils.make_dirs(usb_mgr_config.temp_dir, log)
    _run_mgr(log)

