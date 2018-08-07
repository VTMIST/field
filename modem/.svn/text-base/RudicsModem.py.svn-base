#!/usr/bin/env python

# Encapsulates the interface to an Iridium modem
# operated in RUDICS modeself._connected

import sys

from datetime       import datetime,timedelta
import logging
import serial
import traceback
import cStringIO
import select

import datefunc
import modem_config
#import lockfile
import logs
import utils

class RudicsModem:
    
    """Control Iridium modem in RUDICS mode
    
    Exported methods:
    dialup() - Connect to the RUDICS server
    hangup() - Disconnect from the RUDICS server
    flushBoth() - Flush the modem serial receive and transmit buffer
    flushIn() - Flush the modem serial receive buffer
    flushOut() - Flush the modem serial transmit buffer
    fileno() - Return the serial port file number
    isConnected() - Return true if modem is connected to Iridium net
    iccid() - Return the ICCID number read from the SIM
    
    """

    def __init__(self, log):
        """Instantiate an RudicsModem object       
        """         
        self._log = log
        self._port = None
        self._connected  = False
        self._iccid = 'coming soon'
        self._raw_response = ''
        self._hw_mgr_server = None
        self._hw_mgr_lock = utils.Lock(self._log)
        
    def _open(self):       
        """Open the modem port and intialize the modem        
        Returns True if the modem was initialized successfully        
        """
        self._connected  = False
        if self._serial_port_is_open():
            self._port.close()
            self._port = None
        m_writeTimeout    = modem_config.write_timeout
        m_writeTimeout    = datefunc.timedelta_as_seconds(m_writeTimeout)
        m_readTimeout     = modem_config.read_timeout
        m_readTimeout     = datefunc.timedelta_as_seconds(m_readTimeout)

        # Use mgetty compatible lock
        # mgetty also uses this port as a back door console.
        # The lock provides modem mutual exclusion.
        #self._lockfile   = lockfile.LockFile(modem_config.lock_file_path, self._log)
        #if not self._lockfile.acquire():
        #    self._log.error('Could not acquire modem lock file')
        #    return False        
        try:
            self._port = serial.Serial(port=modem_config.serial_device,
                                      baudrate=modem_config.baud_rate,
                                      rtscts = 1,
                                      timeout = m_readTimeout,
                                      writeTimeout = m_writeTimeout,
                                      stopbits = serial.STOPBITS_TWO)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
            return False
        if self._serial_port_is_open():
            self._log.debug('Serial port %s opened' % self._port.portstr)
            self._toggleDTR(delay=10)
        else:
            self._log.error('Serial port %s failed to open' % self._port.portstr)
            self._close()
            return False
        self._log.debug(self._port)
        modem_up = self._initModem()
        if not modem_up:
            self._close()
        return modem_up
        
    def _modem_is_powered_up(self):
        [status, self._hw_mgr_server] = utils.get_hw_status('irid_pwr', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        if status is None:
            return False
        return status == 1

    def _close(self):
        """Close the serial connection to the modem"""
        if self._serial_port_is_open():
            self._toggleDTR(1)
            #if self._lockfile.ownlock():
            #    self._lockfile.release()
        if self._port:
            self._port.close()
        self._port = None
        self._connected  = False
        self._log.debug('Serial port closed')
            
    def dialup(self):
        """Open the port and connect to Iridium RUDICS service      
        Return True if connected with server        
        """
        if not self._modem_is_powered_up():
            return False           
        if not self._open():
            return False            
        if not self._enterCmdMode():
            return False
            
        conn_try = 1
        startTime = datetime.now()
        while conn_try <= modem_config.connect_tries:
            self._log.debug('Dialup attempt %s' % conn_try)          
            if self._connect():
                elapsedTime = datetime.now() - startTime
                self._log.info('Connected')
                self._connected  = True
                return True
            utils.wait(5)
            conn_try += 1
        self._log.debug('Dialup failed')
        self.hangup()
        self._close()
        return False
        
    def hangup(self):
        """Hang up the modem and close the port"""
        if not self._modem_is_powered_up():
            return           
        if self._enterCmdMode():
            self._send('ATH0')
        self._close()
            
    def flushBoth(self):
        """Flush the modem serial receive and transmit buffer"""
        self.flushIn()
        self.flushOut()

    def flushIn(self):
        """Flush the modem serial receive buffer"""
        if self._serial_port_is_open():
            self._port.flushInput()
    
    def flushOut(self):
        """Flush the modem serial transmit buffer"""
        if self._serial_port_is_open():
            self._port.flushOutput()
        
    def fileno(self):
        """Return the file number for serial port data"""
        if self._serial_port_is_open():
            return self._port.fileno()
        return -1
        
    def isConnected(self):
        return self._connected \
                and self._serial_port_is_open() \
                and self._port.getCD()
        
    def iccid(self):
        return self._iccid                                
           
    def _serial_port_is_open(self):
        try:
            is_open = self._port and self._port.isOpen()
        except:
            return False
        return is_open
            
    def _connect(self):
        """Connect to the RUDICS service       
        Return True if successful       
        """
        self._log.debug('Dialing')
        self.flushBoth()
        
        return self._send('ATDT %s' % modem_config.rudics_phone_number, 'open<CR><LF>',
                    timeout=modem_config.connect_timeout)
            
    def _send(self, tx_str, expect='OK<CR><LF>', reject='NO CARRIER<CR><LF>', timeout=10):
        """Send a string to the modem and wait for a response
        
        Arguments
        tx_str - the string to be sent
        expect - the nominal case expected response
        reject - raise an IOError if this response received
        timeout - integer seconds or timedelta      
        
        Return True modem response contains expect
        Return False modem response contains reject
        Return False timeout is exceeded
        Return False if the serial port is closed
        
        """
        if not self._serial_port_is_open():
            return False
        csq_cmd = (tx_str == 'AT+CSQF')
        #self._log.info('Sending: %s', tx_str.strip())
        self.write(tx_str + '\r')

        self._raw_response = ''
        response = ''
        output = ''
        if isinstance(timeout, int):
            timeout = timedelta(seconds=timeout)
        endtime = datetime.now() + timeout

        poller = select.poll()
        poller.register(self._port.fd, select.POLLIN)

        while True:
            events = poller.poll(1000)
            if events:
                s = self.read(1)
                if s is None:
                    return False    # serial port closed
                self._raw_response += s
                response += s
                output = response.replace('\r', '<CR>').replace('\n', '<LF>')
            if output.strip().endswith(expect):
                #self._log.debug('from modem: %s' % output)
                if csq_cmd:
                    self._log.info('Signal strength is %s' % self._strip_out_csq(self._raw_response))
                return True
            if reject and output.strip().endswith(reject):
                #self._log.debug('from modem: %s' % output)
                return False
            if output.endswith('<CR><LF>'):
                #self._log.debug('from modem: %s' % output)
                output = ''
                response = ''
            if datetime.now() > endtime:
                #self._log.debug('from modem: %s' % output)
                self._log.debug('Timeout on %s' % tx_str.replace('\r', '<CR>'))
                return False
                
    def _sendCmd(self, command):
        """Send a command to the modem
        
        Return True if the command response was 'OK'
        
        """
        return self._send(command)              
                   
    def write(self, data):
        """Write a string to the modem"""
        if self._serial_port_is_open():
            #self._log.debug('to modem:   %s' % data)
            try:
                self._port.write(data)
            except serial.SerialTimeoutException:
                self._log.info('Exception: Serial port write timeout')
            except KeyboardInterrupt:
                raise
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)    
        
    def read(self, num=None):
        """Read data from the serial port receive buffer
        
        Arguments:
        num = Number of bytes to return.
              If num is None return all available bytes
              
        Return None if serial port is closed
              
        """
        if not self._serial_port_is_open():
            return None

        if num is None:
            num = self._port.inWaiting()
        return self._port.read(num)
        
    def _toggleDTR(self, delay=10):
        self._log.debug('Toggling DTR')
        self._lowerDTR()
        utils.wait(delay)
        self._raiseDTR()
        
    def _raiseDTR(self):
        """Set serial port DTR output to high"""
        if self._serial_port_is_open():
            try:
                self._port.setDTR(1)
            except serial.SerialException, e:
                self._log.error('RudicsModem._raiseDTR exception: %s' % e)    
            self._log.debug('DTR lowered')
    
    def _lowerDTR(self):
        """Set serial port DTR output to low"""
        if self._serial_port_is_open():
            try:
                self._port.setDTR(0)
            except serial.SerialException, e:
                self._log.error('RudicsModem._lowerDTR exception: %s' % e)    
            self._log.debug('DTR lowered')
            
    def _enterCmdMode(self):
        """Force the modem into command mode
        
            Return True if modem is in command mode
            
        """
        if self._serial_port_is_open():
            if self._send('AT'):
                return True
            utils.wait(1)
            self.write('+++')
            utils.wait(3)
            if self._send('AT'):
                return True
            if self._send('AT'):
                return True
        return False            


    def _initModem(self):
        """Send configuration commands to the modem
        
        Return True if all commands were successful
        
        """
        if not self._serial_port_is_open():
            return False
        self._port.write('\r')
        utils.wait(1)
        self.flushBoth()
        # 'AT&F0=0' = restore factory defaults
        # 'ATE0' = turn command echo off
        # 'AT+CBST=71,0,1' = NAL recommended setup cmd
        # 'AT&S0=1' = auto answer after one ring
        # 'AT&K3' = enable RTS, CTS
        # 'ATS12=150' = set the +++ guard time to 150 msec
        # 'AT&D2 = set DTR mode to 2 (see manual)
        # 'AT+CSQF = get the RF signal quality
        # 'AT+CICCID' = get the ICCID from the SIM
        ret_val = self._sendCmd('AT') and \
               self._sendCmd('AT&F0=0') and \
               self._sendCmd('ATE0') and \
               self._sendCmd('AT+CBST=71,0,1') and \
               self._sendCmd('AT&S0=1') and \
               self._sendCmd('AT&K3') and \
               self._sendCmd('ATS12=150') and \
               self._sendCmd('AT&D2') and \
               self._sendCmd('AT+CSQF') and \
               self._sendCmd('AT+CICCID')
               
        # Pull the SIM ICCID out of the most recent
        #  response from the modem.
        #self._log.debug('ICCID as read from the modem %s:' % self._raw_response)
        self._iccid = self._strip_out_iccid(self._raw_response)
        return ret_val
               
    def _strip_out_iccid(self, raw):
        """Strip out and return the ICCID from the raw modem response"""
        iccid = ''
        for ch in raw:
            if ch.isdigit():
                iccid += ch
        return iccid
        
    def _strip_out_csq(self, raw):
        """Strip out and return the signal strength from the raw modem response"""
        strength = '?'
        for ch in raw:
            if ch.isdigit():
                strength = ch
                break
        return strength + ' of 5'                                    
        
def _runTest(log):
    """Run basic modem module tests"""
    irid = RudicsModem(log)
    
    # Test dialup method
    log.debug('')
    log.debug(' ****** Starting modem module test ******')
    print 'Testing dialup method'
    
    if irid.dialup():     
        print 'Connected to RUDICS server'
        msg_ID = 1
        
        while True:
            test_msg = 'Msg %s:' % str(msg_ID)
            msg_ID += 1
            irid.write(test_msg)
            print 'sent %s' % test_msg
            data = irid.read()
            if data is None:
                print 'Serial port closed'
                break
            else:
                print 'received %s' % data
            if not irid.isConnected():
                print 'Connection dropped'
                break
            utils.wait(2)                
    else:
        print 'dialup method failed'
     
    print 'hanging up'
    irid.hangup()
    utils.wait_for_child_threads()
    print 'All done'

if __name__ == '__main__':
    """Test the RudicsModem class"""
    print "Testing RudicsModem class"
    log = logs.open(modem_config.log_name_modem, modem_config.log_dir, logging.DEBUG)
    try: 
        _runTest(log)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        print 'Exception raised.  See log file'
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
    
