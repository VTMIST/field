# Generally useful utilities

import time
import traceback
import cStringIO
import threading
import socket
import Queue
import xmlrpclib
import subprocess
import socket
import fcntl
import struct
import sys
import os
import os.path
import shutil
from datetime import datetime,timedelta
from errno import EINTR
import commands

import hw_mgr_config
import usb_mgr_config


def wait(wait_secs):
    """
    Wait a specified number of seconds

    Use floating point number of seconds for higher resolution
    """
    # Sleep in a try block to allow
    # KeyboardInterrupt to end sleep
    while True:
        try:
            time.sleep(wait_secs)
        except OSError, e:
            if e.errno == EINTR:
                continue
        except Exception:
            raise
            return
        break


def log_exc_traceback(exc_type, exc_value, exc_traceback, log):
    """Write exception traceback information to log

    Arguments:
    exc_type - obtained from sys.exc_info() by caller
    exc_value - obtained from sys.exc_info() by caller
    exc_traceback - obtained from sys.exc_info() by caller
    log - the log to be written to

    """
    # Suppress all exceptions while logging an exception
    #  to prevent infinite loop
    print 'Exception occurred!!!  See %s log file' % log.name
    try:
        trace_str = cStringIO.StringIO()
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                    limit=None, file=trace_str)
        log.error(trace_str.getvalue())
    except:
        pass


def get_ip_address(ifname):
    """Get the IP address assigned to a network interface.

    ifname is typically 'eth0'

    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


def get_peer_addr_str(sock):
    """Get sock's peer address in xxx.xxx.xxx.xxx:pppp format"""
    addr_port = '0.0.0.0:0000'
    # Use try block in case socket is closed
    try:
        addr, port = sock.getpeername()
        addr_port = (''.join((addr, ':', str(port))))
    except socket.error:
        pass
    return addr_port

def get_sock_addr_str(sock):
    """Get sock's address in xxx.xxx.xxx.xxx:pppp format"""
    addr_port = '0.0.0.0:0000'
    # Use try block in case socket is closed
    try:
        addr, port = sock.getsockname()
        addr_port = (''.join((addr, ':', str(port))))
    except socket.error:
        pass
    return addr_port

def get_peer_port(sock):
    """Get sock's peer port number"""
    port = 0
    # Use try block in case socket is closed
    try:
        addr, port = sock.getpeername()
    except socket.error:
        pass
    return port

def get_sock_port(sock):
    """Get sock's port number"""
    port = 0
    # Use try block in case socket is closed
    try:
        addr, port = sock.getsockname()
    except socket.error:
        pass
    return port


def close_sock(sock):
    """Close a socket.  Ignore socket errors.

    Useful for closing a socket that may
    already be closed.

    """
    try:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    except socket.error:
        pass


def q_flush(q):
    """Flush a queue"""
    while not q.empty():
        q.get()


def q_get(q, get_timeout=10):
    """ Read from a queue with timeout.
    timeout is integer or floating point seconds.
    Return None if timeout.
    """
    block = True
    if get_timeout == 0:
        block = False
    try:
        return q.get(block, timeout=get_timeout)
    except Queue.Empty:
        return None


def wait_for_child_threads():
    """Wait for all child threads to exit

    This is used before exiting programs that
    create child threads.  If this is not called
    before exiting the program, the log file will
    be closed before the threads exit.  Exceptions
    are generated if a thread writes to a log file
    after the log file is closed

    """
    timer = time.time()
    while threading.activeCount() > 1:
        if time.time() > (timer + 60):
            print 'Timed out waiting for child threads to die'
            break
        wait(0.5)


def build_test_data_buffer(size=500):
    """Return a string full of test data values

    Test values are sequential 1 to 255 (no zeros)

    """
    test_data = ''
    test_val = 1
    for i in range(0, size):
        test_data += chr(test_val)
        test_val += 1
        if test_val == 256:
            test_val = 1
    return test_data


def byte_buf_to_ord(byte_buf):
    """Convert a string of bytes to a string of printable decimal numbers"""
    printable = ''
    for c in byte_buf:
        printable += str(ord(c))
        printable += ' '
    return printable


def str_sum(data):
    """Return the sum of the bytes in a string"""
    if data is None:
        return 0
    sum = 0
    for x in data:
        sum += ord(x)
    return sum


def bytes_to_hex(byteStr):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    # Uses list comprehension which is a fractionally faster implementation than
    # the alternative, more readable, implementation below
    #
    #    hex = []
    #    for aChar in byteStr:
    #        hex.append( "%02X " % ord( aChar ) )
    #
    #    return ''.join( hex ).strip()

    return ''.join( [ "0x%02X " % ord( x ) for x in byteStr ] ).strip()



class ThreadSkeleton(threading.Thread):
    """

    """
    def __init__(self, log, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._exit_callback = exit_callback
        self._children = []
        self._stop_event = threading.Event()
        self.name = 'ThreadSkeleton'
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
            utils.wait(0.5)

        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        for ch in self._children:
            ch.stop()
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)

    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        pass

    def is_running(self):
        return self._running

    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()


def process_is_running(exe_file_name, log=None):
    """ Return True if the exe_file_name process is running """
    (output, error) = call_subprocess('ps -A', log)
    lines = output.splitlines()
    for line in lines:
        if (line.find(exe_file_name) != -1) \
                and (line.find('tail') == -1) \
                and (not line.endswith(']')):
            return True
    return False


def start_process(exe_file_name, log=None):
    """Start a process if it is not already running

    Wait for the process to start
    """
    if not process_is_running(exe_file_name):
        while True:
            try:
                proc = subprocess.Popen(exe_file_name)
                wait(0.01) # workaround for subprocess.Popen thread safety bug
            except OSError, e:
                if e.errno == EINTR:
                    continue
            break
        if log:
            log.info('Starting %s' % (exe_file_name))
        timer = time.time()
        while not process_is_running(exe_file_name):
            if time.time() > (timer + 60):
                print 'Timed out waiting for process to start'
                break
            wait(0.25)


def call_subprocess(exe_and_args, log=None):
    """Run a subprocess, wait for subprocess termination
    and return the subprocess stdout and stderr output.
    exe_and_args can be a string or a sequence.
    Return [None, None] if failed.
    """
    if not isinstance(exe_and_args, str):
        cmd = ' '.join(exe_and_args)
    else:
        cmd = exe_and_args
    output = commands.getoutput(cmd)
    return [output, '']



# Old version that caused random crashes when
# subprocesses were called from threaded code.
# Traced to a known bug in subprocess.Popen.
# commands.getoutput() seems to work fine.
#def call_subprocess(exe_and_args, log=None):
    """Run a subprocess, wait for subprocess termination
    and return the subprocess stdout and stderr output.
    exe_and_args can be a string or a sequence.
    Return [None, None] if failed.
    """
    """
    if isinstance(exe_and_args, str):
        exe_and_arg_list = exe_and_args.split(' ')
    else:
        exe_and_arg_list = exe_and_args
    while True:
        try:
            proc = subprocess.Popen(exe_and_arg_list,
                                    bufsize=4096,
                                    executable=None,
                                    stdin=None,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            wait(0.01) # workaround for subprocess.Popen thread safety bug
            (con_out, con_err) = proc.communicate()
        except OSError, e:
            if e.errno == EINTR:
                continue
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if log:
                log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            return (None, None)
        break
    if log:
        log.info('call_subprocess: cmd    = %s' % exe_and_args)
        log.info('call_subprocess: output = %s' % con_out)
        log.info('call_subprocess: error  = %s' % con_err)
    return (con_out, con_err)
    """


# Stop a process given its executable file name.
# Uses kill to send a SIGINT to the process.
# If SIGINT doesn't work 'kill -9' is sent.
def stop_process_by_name(exe_file_name, log=None):
    if not process_is_running(exe_file_name):
        if log:
            log.info('stop_process_by_name: %s is not running' % exe_file_name)
        return

    # Kill all the processes(threads) spawned by exe_file_name
    # Killing the parent should do the job, but kill
    #  all the subprocesses individually just to make sure.
    (output, error) = call_subprocess('ps', log)
    lines = output.splitlines();
    for line in lines:
        if (line.find(exe_file_name) != -1) \
                and (line.find('tail') == -1):
            fields = line.split()
            try:
                pid = int(fields[0])
                if log:
                    log.info('stop_process_by_name: pid = %s' % str(pid))
            except TypeError:
                if log:
                    log.error('stop_process_by_name: Could determine pid for %s' % (exe_file_name))
                return

            # Ask the process politely to shut down
            cmd = 'kill -s INT %s' % str(pid)
            if log:
                log.info('stop_process_by_name: executing cmd: %s' % cmd)
            call_subprocess(cmd, log)

            # Wait a while for the process to shut down
            timer = time.time()
            while process_is_running(exe_file_name, log):
                if time.time() > (timer + 60):
                    print 'stop_process_by_name: Timed out waiting for process to stop, executing kill -9'
                    if log:
                        log.info('stop_process_by_name: Timed out waiting for process to stop, executing kill -9')
                    # Bring in the Terminator!
                    cmd = 'kill -9 %s' % str(pid)
                    call_subprocess(cmd, log)
                    break
                wait(0.25)


def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """ Fork the current process aa a daemon, redirecting standard file
        descriptors (by default, redirects them to /dev/null)
        NOTE: don't do any of this if your daemon gets started by inetd!
        inetd does all you need, including redirecting standard file
        descriptors.  The chdir() and umask() steps are the only ones
        you may still want.
        Copied from the Python Cookbook 2nd Edition.
    """
    # Perform first fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0) # exit first parent
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    # Decouple from parent environment
    os.chdir("/")
    os.umask(0)
    os.setsid()
    # Perform second fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0) #Exit second parent
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    # The process is now daemonized, redirect standard file descriptors
    for f in sys.stdout, sys.stderr: f.flush()
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def make_dirs(dir_path, log=None):
    """ Make a directory if it doesn't already exist.
        Makes all intermediate dirs required.
    """
    if path_exists(dir_path):
        return
    while True:
        try:
            os.makedirs(dir_path)
        except OSError, e:
            if e.errno == EINTR:
                continue
            if log:
                log.error('Could not create directory %s' % dir_path)
            return
        break
    if log:
        log.debug('Created directory %s' % dir_path)


def safe_remove(the_list, the_element):
    """ Remove an element that might be in a list """
    try:
        the_list.remove(the_element)
    except ValueError:
        # the_element was not in the list, no problem
        pass


def copy_file(src_path, dest_path, log):
    """ Copy src file to dest file
        Return True if successful
    """
    while True:
        try:
            shutil.copy2(src_path, dest_path)
        except OSError, e:
            if e.errno == EINTR:
                continue
            log.error('Error copying %s to %s, %s' % (src_path, dest_path, str(why)))
            return False
        break
    log.debug('Copied %s to %s' % (src_path, dest_path))
    return True


def delete_file(file_path, log):
    """ Delete a file if it exists """
    if not path_exists(file_path):
        return
    while True:
        try:
            os.remove(file_path)
        except OSError, e:
            if e.errno == EINTR:
                continue
            log.error('Error: could not delete %s' % file_path)
            return
        break
    log.debug('Deleted %s' % file_path)


def temp_filename(prefix=None, suffix=None):
    """ Return a temporary file name """
    now = datetime.now()
    return ''.join((str(now.day),
                    str(now.hour),
                    str(now.minute),
                    str(now.second),
                    '_',
                    str(now.microsecond),
                    ))


def volume_is_mounted(volume):
    """ Return True if volume is mounted """
    (output, error) = call_subprocess('mount')
    if volume in output:
        return True
    return False


def mount_volume(device, volume, timeout=5, log=None):
    """ Mount volume if it is not already mounted
        Wait until the volume is mounted or timeout
        Return True if successful
    """
    if volume_is_mounted(volume):
        return True
    make_dirs(volume, log)  # creates mount point if needed
    call_subprocess(' '.join(('mount', device, volume)), log)
    start_time = datetime.now()
    timeout_period = timedelta(seconds=timeout)
    while (datetime.now() - start_time) < timeout_period:
        if volume_is_mounted(volume):
            return True
        wait(0.5)
    return False


def unmount_volume(volume, timeout=5):
    """ Unmount volume if it is currently mounted
        Wait until the volume is unmounted or timeout
        Return True if successful
    """
    if not volume_is_mounted(volume):
        return True
    # Use lazy (-l) unmount. Detach the filesystem from the filesystem
    # hierarchy now, and cleanup all references to the filesystem as
    # soon as it is not busy anymore.
    call_subprocess(''.join(('umount -l ', volume)))


def time_stamp_str(time):
    """Convert a time to a time stamp string"""
    return time.strftime("%Y_%m_%d_%H_%M_%S")


def strip_trailing_newline(s):
    """ strip trailing newline in string """
    i = s.rfind('\n')
    if i == len(s) - 1:
        return s[:i]
    else:
        return s


def list_difference(list1, list2):
    """Return a list containing all the elements
    in list1 that are not in list2
    """
    diff_list = []
    for item in list1:
        if not item in list2:
            diff_list.append(item)
    return diff_list


def total_seconds(td):
    """Return a float containing the total number of seconds
        in a timedelta to microsecond resolution"""
    return (float(td.microseconds) + (float(td.seconds) + float(td.days) * 24.0 * 3600.0) * 1000000.0) / 1000000.0


def get_et_secs(start_time):
    """Using time.time(), return seconds since start_time.
    Returns floating point seconds to microsecond resolution
    """
    return time.time() - start_time


def reboot():
    """Reboot the system"""
    call_subprocess('/sbin/reboot')


def reboot_golden_code():
    """Reboot the system with image in /golden_code"""
    call_subprocess('cp /golden_code/image.tar.gz /install')
    call_subprocess('cp /golden_code/image.tar.gz.md5 /install')
    wait(2)
    call_subprocess('/sbin/reboot')


def get_file_size(path):
    while True:
        try:
            size = os.path.getsize(path)
        except OSError, e:
            if e.errno == EINTR:
                continue
        return size


def get_path_basename(path):
    while True:
        try:
            basename = os.path.basename(path)
        except OSError, e:
            if e.errno == EINTR:
                continue
        return basename


def path_exists(path):
    while True:
        try:
            exists = os.path.exists(path)
        except Exception, e:
            if e.errno == EINTR:
                continue
        return exists


def get_file_mod_time(filepath):
    while True:
        try:
            mod_time = os.path.getmtime(filepath)
        except OSError, e:
            if e.errno == EINTR:
                continue
        return mod_time


def expand_user_path(dir):
    while True:
        try:
            expanded = os.path.expanduser(dir)
        except OSError, e:
            if e.errno == EINTR:
                continue
        return expanded


class Lock:
    """General lock class"""
    def __init__(self, log):
        self._lock = threading.Lock()
        self._log = log

    def acquire(self):
        while not self._lock.acquire(False):
            wait(0.1)
        #self._log.debug('Acquired lock')

    def release(self):
        self._lock.release()
        #self._log.debug('Released lock')


def set_power_state(device, state, server_proxy, hw_mgr_lock, log=None):
    """Turn a device on or off using hw_mgr.
    state = 'on' | 'off'
    Return the server proxy if successful,
      None if not successful.
    """
    hw_mgr_lock.acquire()
    attempt = 1
    while (attempt <= 2):
        if server_proxy is None:
            server_proxy = get_XMLRPC_server_proxy(hw_mgr_config.XMLRPC_URL, log)
            if server_proxy is None:
                hw_mgr_lock.release()
                return None
        try:
            server_proxy.set_power(device, state)
        except xmlrpclib.ProtocolError, err:
            if log:
                log.error("utils.set_power_state: XMLRPC protocol exception:")
                log.error("URL: %s" % err.url)
                log.error("HTTP/HTTPS headers: %s" % err.headers)
                log.error("Error code: %d" % err.errcode)
                log.error("Error message: %s" % err.errmsg)
            server_proxy = None
            attempt += 1
            continue    # retry in case bad hw_mgr_server was passed in
        except Exception, e:
            if log:
                log.error('utils.set_power_state: exception:  %s' % e)
            server_proxy = None
            attempt += 1
            continue    # retry in case bad hw_mgr_server was passed in
        hw_mgr_lock.release()
        return server_proxy
    hw_mgr_lock.release()
    return None


def get_hw_status(value_name, server_proxy, hw_mgr_lock, log=None):
    """Get a status value from hw_mgr
    Return [status_value, hw_mgr_server]
    Return [None, None] if unsucessful.
    """
    hw_mgr_lock.acquire()
    attempt = 1
    while (attempt <= 2):
        if server_proxy is None:
            server_proxy = get_XMLRPC_server_proxy(hw_mgr_config.XMLRPC_URL, log)
            if server_proxy is None:
                hw_mgr_lock.release()
                return [None, None]
        try:
            status_value = server_proxy.get_status(value_name)
        except xmlrpclib.ProtocolError, err:
            if log:
                log.error("utils.get_hw_status: XMLRPC protocol exception:")
                log.error("URL: %s" % err.url)
                log.error("HTTP/HTTPS headers: %s" % err.headers)
                log.error("Error code: %d" % err.errcode)
                log.error("Error message: %s" % err.errmsg)
            server_proxy = None
            attempt += 1
            continue    # retry in case bad server_proxy was passed in
        except Exception, e:
            if log:
                log.error('utils.get_hw_status: exception:  %s' % e)
            server_proxy = None
            attempt += 1
            continue    # retry in case bad hw_mgr_server was passed in
        hw_mgr_lock.release()
        return [status_value, server_proxy]
    hw_mgr_lock.release()
    return [None, None]


def get_full_hw_status(server_proxy, hw_mgr_lock, log):
    """Get the entire status dictionary from hw_mgr
    Return [status_dict, hw_mgr_server]
    Return [None, None] if unsucessful.
    """
    hw_mgr_lock.acquire()
    attempt = 1
    while (attempt <= 2):
        if server_proxy is None:
            server_proxy = get_XMLRPC_server_proxy(hw_mgr_config.XMLRPC_URL, log)
            if server_proxy is None:
                hw_mgr_lock.release()
                return [None, None]
        try:
            status_dict = server_proxy.get_full_status()
        except xmlrpclib.ProtocolError, err:
            log.error("utils.get_full_hw_status: XMLRPC protocol exception:")
            log.error("URL: %s" % err.url)
            log.error("HTTP/HTTPS headers: %s" % err.headers)
            log.error("Error code: %d" % err.errcode)
            log.error("Error message: %s" % err.errmsg)
            server_proxy = None
            attempt += 1
            continue    # retry in case bad server_proxy was passed in
        except Exception, e:
            log.error('utils.get_full_hw_status: exception:  %s' % e)
            server_proxy = None
            attempt += 1
            continue    # retry in case bad hw_mgr_server was passed in
        hw_mgr_lock.release()
        return [status_dict, server_proxy]
    hw_mgr_lock.release()
    return [None, None]


def get_XMLRPC_server_proxy(server_URL, log=None):
    """Create an XMLRPC server proxy for a remote server.
        Return the server proxy or None.
    """
    socket.setdefaulttimeout(10)
    try:
        server_proxy = xmlrpclib.ServerProxy(server_URL)
    except xmlrpclib.ProtocolError, err:
        if log:
            log.error("utils._get_XMLRPC_server_proxy: XMLRPC protocol exception:")
            log.error("URL: %s" % err.url)
            log.error("HTTP/HTTPS headers: %s" % err.headers)
            log.error("Error code: %d" % err.errcode)
            log.error("Error message: %s" % err.errmsg)
        return None
    except Exception, e:
        if log:
            log.error('utils._get_XMLRPC_server_proxy: exception:  %s' % e)
        return None
    return server_proxy


def round_datetime_to_sec(dt):
    """Round a datetime to the nearest second.
        Return [rounded_dt, adj_usecs].
        adj_usecs is the difference between dt and rounded_dt,
            in microseconds.
        Positive adj_usecs means dt was rounded up.
        Negative adj_usecs means dt was rounded down.
    """
    usec = dt.microsecond
    if usec >= 500000:
        adj = 1000000 - usec
    else:
        adj = -usec
    rounded_dt = dt + timedelta(microseconds=adj)
    return [rounded_dt, adj]


# Iridium Time Fix JAN2018
def get_iridium_time():
    """ Look for iridium system time in '/tmp/iridium_time' """
    [iridium_time, stderr] = call_subprocess('cat /tmp/iridium_time')
    if iridium_time == '-MSSTM: no network service':
        # In the event of an error getting iridium network time
        return 9999
    else:
        # We have a good time response
        epoch_counter = int('0x' + iridium_time.lstrip('-MSSTM: '), 0)
        epoch_date = datetime(2014, 5, 11, 14, 23, 55, 00)
        time_diff = (epoch_counter * timedelta(milliseconds=90))
        sync_time = epoch_date + (epoch_counter * timedelta(milliseconds=90))
        if datetime.now() > sync_time:
            # System time ahead of Iridium time (fast)
            sync_age = datetime.now() - sync_time
        else:
            # System time behind Iridium time (slow)
            sync_age = sync_time - datetime.now()
        return int(sync_age.seconds)


class Bunch:
    """A class that is used only to contain
        a bunch of values
    """
    def __init__(self, **kwds):
        self.__dict__.update(kwds)









