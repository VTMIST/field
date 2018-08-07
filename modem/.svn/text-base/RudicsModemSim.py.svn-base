#!/usr/bin/env python

# Simulated Iridium RUDICS modem that connects to
#  the RUDICS server via ethernet

import sys

from datetime       import datetime,timedelta
import logging
import serial
import traceback
import cStringIO
import select
import sys

import datefunc
import modem_config
import lockfile
import logs
import utils
import sock_utils

class RudicsModemSim:
    
    """Control Iridium modem in RUDICS mode
    
    Exported methods:
    dialup() - Connect to the RUDICS server
    hangup() - Disconnect from the RUDICS server
    flushBoth() - Flush the connection receive and transmit buffer
    flushIn() - Flush the connection receive buffer
    flushOut() - Flush the connection transmit buffer
    fileno() - Return the connection file number
    isConnected() - Return true if modem is connected to Iridium net
    iccid() - Return the ICCID number read from the SIM
    
    """

    def __init__(self, log, host=None, port=None):
        """Instantiate an RudicsModemSim object
        
        log = log object
        
        """         
        self._log = log
        self._sock_h = None
        self._host = host
        self._port = port
        self._sock_h = None
        self._connected = False
        self._read_q = None  
        self._write_q = None  
        
    def dialup(self):
        """Connect to the RUDICS server
        
        Return True if connected to server
        
        """
        if self._connected:
            self.hangup()
        sock_h = sock_utils.connect_to_server(self._log,
                                self._host,
                                self._port,
                                exit_callback=self._my_exit_callback)
        if sock_h is None:
            return False
        self._sock_h = sock_h
        self._connected = True
        self._read_q = sock_h.get_read_q()
        self._write_q = sock_h.get_write_q()
        return True            
     
    def _my_exit_callback(self, child):
        """This is called when the socket handler dies"""
        self.hangup()
        
    def hangup(self):
        if self._sock_h is not None:
            self._sock_h.stop()
        self._connected = False
        self._sock_h = None
        self._read_q = None
        self._write_q = None
            
    def flushBoth(self):
        """Flush the connection receive and transmit buffers"""
        self.flushIn()
        self.flushOut()

    def flushIn(self):
        """Flush the connection receive buffer"""
        if self._connected:
            utils.q_flush(self._read_q)
    
    def flushOut(self):
        """Flush the connection transmit buffer"""
        if self._connected:
            utils.q_flush(self._write_q)
        
    def fileno(self):
        """Return the file number for connection data"""
        return None
        
    def isConnected(self):
        return self._connected
        
    def iccid(self):
        return 'Development'               
                   
    def write(self, data):
        """Write a string to the modem"""
        if self._connected:
            self._write_q.put(data)
        
    def read(self):
        """Read all available data from the connection receive buffer
              
        Return None if the connection is closed
              
        """
        if not self._connected:
            return None
        parts = []
        while not self._read_q.empty():
            parts.append(self._read_q.get())
        return ''.join(parts)
               
def _runTest(log):
    print 'No test available'

if __name__ == '__main__':
    """Test the RudicsModemSim class"""
    print "Testing RudicsModemSim class"
    log = logs.open(modem_config.log_name_modem,
                    modem_config.log_dir,
                    logging.DEBUG)
    try: 
        _runTest(log)
    except KeyboardInterrupt:
        log.info('KeyboardInterrupt (ignored)')
    except:
        print 'Exception raised.  See log file'
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
    
