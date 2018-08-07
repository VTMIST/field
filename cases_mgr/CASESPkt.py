#! /usr/bin/python

# CASESPkt is a class that encapsulates a CASES Message Packet

# CASES Packet Structure
# ----------------------
# Byte 0: sync code byte 0 = 0x55
# Byte 1: sync code byte 1 = 0xAA
# Byte 2: sync code byte 2 = 0x33
# Byte 3: sync code byte 3 = 0xCC
# Byte 4: length byte MSB (covers type and data fields only)
# Byte 5: length byte 2nd MSB
# Byte 6: length byte 3rd MSB
# Byte 7: length byte LSB
# Byte 8: packet type byte
# Byte 9: first data byte
# Byte N: last data byte
# Byte N + 1: checksum MSB
# Byte N + 2: checksum LSB
# 
# Packet Types:
# 0x01 = Soft reset command. No data.
# 0x02 = Hard reset command. No data.
# 0x10 = Upload DSP image command. Data is binary DSP image.
# 0x11 = Upload DSP configuration command. Data is DSP configuration.
# 0x12 = Upload SBC configuration command. Data is SBC configuration.
# 0x20 = Set power state command.
#       Data field contents:
#           Byte 0: Power state
#                   0 = Sleep
#                   1 = Low
#                   2 = Intermediate
#                   3 = Full
# 0x30 = Query status command. No data.
# 0x38 = Retrieve File (request file from SBC)
#       Data field: filename string (no string termination)
# 0x40 = Execute system command
#       Data field: shell command to be executed by the SBC
# 0x80 = Report status message.
#       Data field contents:
#           Byte 0: Status MSB (unused)
#           Byte 1: Status 2nd MSB (unused)
#           Byte 2: Status 3rd MSB (unused)
#           Byte 3: Status MSB
#                   Bit 0: 1 = Instrument is healthy
#                   Bit 1: 1 = Unusual TEC values detected
#                   Bit 2: 1 = Scintillation detected
#                   Bit 3: 1 = Invalid message detected
#                   Bits 4 - 7: unused
# 0x88 = Report batch message. Data is binary report batch.
# 0x89 = Report IQ batch message. Data is binary report batch.
# 0xE0 = Transfer File (to or from SBC)
#       Data field: filename, 0x0A (unix newline), file data      

import sys

import utils

class CASESPkt:
    """Encapsulate a CASES packet"""
    
    # Pkt byte offsets
    SYNC_BYTE_0 = 0
    SYNC_BYTE_1 = 1
    SYNC_BYTE_2 = 2
    SYNC_BYTE_3 = 3
    LEN_MSB = 4
    LEN_2ND_MSB = 5
    LEN_3RD_MSB = 6
    LEN_LSB = 7
    TYPE = 8
    DATA = 9
    
    # Packet types
    SOFT_RESET_CMD = 0x01
    HARD_RESET_CMD = 0x02
    UPLOAD_DSP_IMAGE_CMD = 0x10
    UPLOAD_DSP_CONFIG_CMD = 0x11
    UPLOAD_SBC_CONFIG_CMD = 0x12
    SET_POWER_STATE_CMD = 0x20
    QUERY_STATUS_CMD = 0x30
    RETRIEVE_FILE_CMD = 0x38
    EXECUTE_SYS_CMD = 0x40
    REPORT_STATUS_MSG = 0x80
    REPORT_BATCH_MSG = 0x88
    REPORT_IQ_BATCH_MSG = 0x89
    TRANSFER_FILE_MSG = 0xE0

    
    # Sync byte values
    SYNC_BYTE_0_VALUE = '\x55'
    SYNC_BYTE_1_VALUE = '\xAA'
    SYNC_BYTE_2_VALUE = '\x33'
    SYNC_BYTE_3_VALUE = '\xCC'
    SYNC_CODE_STR = ''.join((SYNC_BYTE_0_VALUE,
                            SYNC_BYTE_1_VALUE,
                            SYNC_BYTE_2_VALUE,
                            SYNC_BYTE_3_VALUE))
        
    # Misc pkt attributes
    HDR_LEN = 9
    # Remember packet length only includes type and data fields
    MIN_PKT_LEN = 1
    MAX_PKT_LEN = 1024 * 200
    CKSUM_LEN = 2
       
    def __init__(self, pkt_buf=''):
        """Create a packet object
        """
        self._pkt_buf = pkt_buf
        
    def build(self, type, data=None):
        """Build a packet from type and data
            
        Store the new packet in self._pkt_buf
        Return self._pkt_buf
        """
        # For speed, build the pkt using only
        #  one string concatenation operation
        parts = []
        #print 'SYNC_CODE_STR is %s' % utils.bytes_to_hex(parts[0])
        if (data is None) or (len(data) == 0):
            data_len = 0
        else:
            data_len = len(data)
        pkt_len = data_len + 1
        
        len_msb = (pkt_len & 0xff000000) >> 24
        len_2nd_msb = (pkt_len & 0x00ff0000) >> 16
        len_3rd_msb = (pkt_len & 0x0000ff00) >> 8       
        len_lsb = pkt_len & 0xff
        
        parts.append(CASESPkt.SYNC_CODE_STR)
        parts.append(chr(len_msb))
        parts.append(chr(len_2nd_msb))
        parts.append(chr(len_3rd_msb))
        parts.append(chr(len_lsb))
        parts.append(chr(type))
        if data_len > 0:
            parts.append(data)       
        cksum = (type + utils.str_sum(data)) & 0xFFFF        
        parts.append(chr(cksum / 256))
        parts.append(chr(cksum % 256))
        self._pkt_buf = ''.join(parts)
        return self._pkt_buf
        
    def get_pkt_buf(self):
        """Return a string containing the entire packet"""
        return self._pkt_buf
                
    def get_data(self):
        """Return the data field"""
        try:
            data_len = self.get_data_len()
            return self._pkt_buf[CASESPkt.DATA:CASESPkt.DATA + data_len]
        except IndexError:
            print 'IndexError in CASESPkt.get_data()'
            return ''
            
    def get_data_len(self):
        """Return the number of data bytes"""
        return self.get_len() - 1
        
    def get_pkt_len(self):
        """Return the total number of bytes in the packet"""
        return self.get_data_len() + 11
    
    def get_len(self):
        """Return the ordinate of the length field"""
        try:
            return ((ord(self._pkt_buf[CASESPkt.LEN_MSB])     << 24) \
                    | (ord(self._pkt_buf[CASESPkt.LEN_2ND_MSB]) << 16) \
                    | (ord(self._pkt_buf[CASESPkt.LEN_3RD_MSB]) <<  8) \
                    |  ord(self._pkt_buf[CASESPkt.LEN_LSB]))
        except IndexError:
            print 'IndexError in CASESPkt.get_len()'
            return 0
    
    def get_type(self):
        """Return the ordinate of the type field"""
        try:
            return ord(self._pkt_buf[CASESPkt.TYPE])
        except IndexError:
            print 'IndexError in CASESPkt.get_type()'
            return 0
            
    def get_cksum(self):
        """Return the contents of the packet checksum field as an integer"""
        pkt_len = self.get_len() + 10
        try:
            msb = ord(self._pkt_buf[pkt_len - 2])
            lsb = ord(self._pkt_buf[pkt_len - 1])
        except IndexError:
            print 'IndexError in CASESPkt.get_cksum()'
            return 0
        return (msb << 8) | lsb
                                                  
    def cksum_is_valid(self):
        """Return True if the pkt checksum is valid"""
        try:
            pkt = self._pkt_buf
            data_len = self.get_data_len()
            calc_cksum = (ord(pkt[CASESPkt.TYPE]) + \
                    utils.str_sum(pkt[CASESPkt.DATA:CASESPkt.DATA + data_len])) & 0xFFFF                              
            cksum_msb = ord(pkt[CASESPkt.DATA + data_len])       
            cksum_lsb = ord(pkt[CASESPkt.DATA + data_len + 1])       
            stored_cksum = (cksum_msb << 8) | cksum_lsb
        except IndexError:
            print 'IndexError in CASESPkt.cksum_is_valid()'
            return False
        return calc_cksum == stored_cksum
        
    def type_str(self):
        """Return the packet type as a printable string"""
        type = self.get_type()
        if type == CASESPkt.SOFT_RESET_CMD:
            return('soft reset cmd')
        elif type == CASESPkt.HARD_RESET_CMD:
            return('hard reset cmd')
        elif type == CASESPkt.UPLOAD_DSP_IMAGE_CMD:
            return('upload DSP image cmd')
        elif type == CASESPkt.UPLOAD_DSP_CONFIG_CMD:
            return('upload DSP configuration cmd')
        elif type == CASESPkt.UPLOAD_SBC_CONFIG_CMD:
            return('upload SBC configuration cmd')
        elif type == CASESPkt.SET_POWER_STATE_CMD:
            return('set power state cmd')
        elif type == CASESPkt.QUERY_STATUS_CMD:
            return('query status cmd')
        elif type == CASESPkt.REPORT_STATUS_MSG:
            return('report status message')
        elif type == CASESPkt.REPORT_BATCH_MSG:
            return('report batch message')
        elif type == CASESPkt.REPORT_IQ_BATCH_MSG:
            return('report IQ batch message')
        elif type == CASESPkt.RETRIEVE_FILE_CMD:
            return('retrieve file cmd')
        elif type == CASESPkt.TRANSFER_FILE_MSG:
            return('transfer file message')
        elif type == CASESPkt.EXECUTE_SYS_CMD:
            return('execute system command')
        else:
            return('unknown type')

    def data_str(self):
        """Return a printable string containing the first 16 bytes of pkt data"""
        data_len = self.get_data_len()
        max_disp_data_len = 16
        if data_len > max_disp_data_len:
            return('first %s bytes of data = %s' % (str(max_disp_data_len),
                            utils.bytes_to_hex(self.get_data()[:max_disp_data_len])))
        else:
            return('data = %s' % utils.bytes_to_hex(self.get_data()[:data_len]))

        
    def str(self):
        """Return the pkt contents in printable form"""
        try:
            parts = []
            sync_code = self._pkt_buf[:CASESPkt.SYNC_BYTE_3 + 1]
            parts.append('  sync code = %s' % utils.bytes_to_hex(sync_code))
            if sync_code == CASESPkt.SYNC_CODE_STR:
                parts.append(' (valid)\n')
            else:
                parts.append(' (NOT valid)\n')
            parts.append('  length = %s' % str(self.get_len()))
            if len(self._pkt_buf) == self.get_pkt_len():
                parts.append(' (valid)\n')
            else:
                parts.append(' (NOT valid)\n')
            parts.append('  type = %s' % str(self.get_type()))
            parts.append(''.join([' (', self.type_str(), ')\n']))
           
            parts.append(''.join(['  ', self.data_str(), '\n']))
           
            pkt_len = self.get_len() + 10
            parts.append('  checksum = %s' % \
                    utils.bytes_to_hex(self._pkt_buf[pkt_len - 2:]))
            if (self.cksum_is_valid()):
                parts.append(' (valid)')
            else:
                parts.append(' (NOT valid)')
            return ''.join(parts)
        except IndexError:
            print 'IndexError in CASESPkt.str()'
            return ''
            
            
def type_and_length_are_valid(pkt_type, pkt_length):
    """Return True if pkt_type is valid and pkt_length
    is valid for the packet type
    """
    if (pkt_type == CASESPkt.SOFT_RESET_CMD) \
        or (pkt_type == CASESPkt.HARD_RESET_CMD) \
        or (pkt_type == CASESPkt.QUERY_STATUS_CMD):
        return pkt_length == CASESPkt.MIN_PKT_LEN
        
    if (pkt_type == CASESPkt.UPLOAD_DSP_IMAGE_CMD) \
        or (pkt_type == CASESPkt.UPLOAD_DSP_CONFIG_CMD) \
        or (pkt_type == CASESPkt.UPLOAD_SBC_CONFIG_CMD) \
        or (pkt_type == CASESPkt.RETRIEVE_FILE_CMD) \
        or (pkt_type == CASESPkt.TRANSFER_FILE_MSG) \
        or (pkt_type == CASESPkt.EXECUTE_SYS_CMD) \
        or (pkt_type == CASESPkt.REPORT_IQ_BATCH_MSG)\
        or (pkt_type == CASESPkt.REPORT_BATCH_MSG):
        return pkt_length <= CASESPkt.MAX_PKT_LEN
        
    if (pkt_type == CASESPkt.SET_POWER_STATE_CMD): 
        return pkt_length == CASESPkt.MIN_PKT_LEN + 1;
        
    if (pkt_type == CASESPkt.REPORT_STATUS_MSG): 
        return pkt_length == CASESPkt.MIN_PKT_LEN + 4;
    return False   
        
       
def SoftResetPkt():
    """Return a string containing a soft reset command packet"""
    pkt = CASESPkt()
    return pkt.build(CASESPkt.SOFT_RESET_CMD)
        
def HardResetPkt():
    """Return a string containing a hard reset command packet"""
    pkt = CASESPkt()
    return pkt.build(CASESPkt.HARD_RESET_CMD)
    
def UploadDSPImageCmdPkt(dsp_image):
    """Return a string containing an upload DSP image cmd packet.
    dsp_mage is a string of bytes.
    """
    pkt = CASESPkt()
    return pkt.build(CASESPkt.UPLOAD_DSP_IMAGE_CMD, dsp_image)

def UploadDSPConfigCmdPkt(dsp_config):
    """Return a string containing an upload DSP config cmd packet.
    dsp_config is a string of bytes
    """
    pkt = CASESPkt()
    return pkt.build(CASESPkt.UPLOAD_DSP_CONFIG_CMD, dsp_config)

def UploadSBCConfigCmdPkt(sbc_config):
    """Return a string containing an upload SBC config packet
    sbc_config is a string of bytes.
    """
    pkt = CASESPkt()
    return pkt.build(CASESPkt.UPLOAD_SBC_CONFIG_CMD, sbc_config)

def SetPowerStateCmdPkt(power_state):
    """Return a string containing a set power state cmd packet.
    power_state is a single byte string.
    """
    if not (len(power_state) == 1):
        return Null
    pkt = CASESPkt()
    return pkt.build(CASESPkt.SET_POWER_STATE_CMD, power_state)

def QueryStatusCmdPkt():
    """Return a string containing a query status cmd packet"""
    pkt = CASESPkt()
    return pkt.build(CASESPkt.QUERY_STATUS_CMD)

def ReportStatusMsgPkt(status):
    """Return a string containing a report status message packet.
    status is a string of bytes
    """
    if not (len(status) == 4):
        return Null
    pkt = CASESPkt()
    return pkt.build(CASESPkt.REPORT_STATUS_MSG)

def ReportBatchMsgPkt(report_batch):
    """Return a string containing a report batch message packet.
    report_batch is a string of bytes
    """
    pkt = CASESPkt()
    return pkt.build(CASESPkt.REPORT_BATCH_MSG)


   
if __name__ == '__main__':
    print 'Starting CASESPkt test'
    pkt = CASESPkt()
    
    pkt.build(CASESPkt.SOFT_RESET_CMD)
    print "Building a soft reset command packet: "
    print pkt.str()
        
    print "Building an upload DSP image packet with 7 data bytes: "
    pkt.build(CASESPkt.UPLOAD_DSP_IMAGE_CMD, data='\x01\x02\x03\x04\x05\x06\x07')
    print pkt.str()
        
    print "Building an upload DSP image packet with 21 data bytes: "
    pkt.build(CASESPkt.UPLOAD_DSP_IMAGE_CMD, data='\x01\x02\x03\x04\x05\x06\x07' * 3)
    print pkt.str()
    print 'Created a new packet from the previous packet'
    pkt = pkt.get_pkt_buf()[:]
    pkt = CASESPkt(pkt)
    print pkt.str()
    
    print "Corrupting sync code"
    good_buf = pkt.get_pkt_buf()[:]
    bad_buf = good_buf[:]
    bad_buf = ''.join((bad_buf[:CASESPkt.SYNC_BYTE_3], chr(0),
                    bad_buf[CASESPkt.SYNC_BYTE_3 + 1:]))
    pkt = CASESPkt(pkt_buf=bad_buf)
    print pkt.str()
    
    print "Corrupting length"
    bad_buf = good_buf[:]
    good_len_lsb = ord(bad_buf[CASESPkt.LEN_LSB])
    bad_buf = ''.join((bad_buf[:CASESPkt.LEN_LSB], chr(good_len_lsb - 1),
                    bad_buf[CASESPkt.LEN_LSB + 1:]))    
    pkt = CASESPkt(pkt_buf=bad_buf)
    print pkt.str()
              
    print 'Exiting CASESPkt test'
    
    

        
