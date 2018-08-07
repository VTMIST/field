#! /usr/bin/python

# ProxyPkt is a class that encapsulates a Proxy Packet

# Proxy Packet Structure
# ----------------------
# Byte 0: sync code byte 0 = 0xAA
# Byte 1: sync code byte 1 = 0x55
# Byte 2: sync code byte 2 = 0x0F
# Byte 3: sync code byte 3 = 0xF0
# Byte 4: length byte LSB (total packet length)
# Byte 5: length byte MSB
# Byte 6: packet type byte
# Byte 7: first data byte
# Byte N: last data byte
# Byte N + 1: checksum LSB
# Byte N + 2: checksum MSB
# 
# Packet Types:
# 0 = Passthrough
#     Data field contents:
#         Byte 0: Source port LSB
#         Byte 1: Source port MSB
#         Byte 2: Destination port LSB
#         Byte 3: Destination port MSB
#         Bytes 4 through N: passthrough data
# 
# 1 = ICCID Request
#     Data field contents: None
#     
# 2 = ICCID
#     Data field contents:
#         Bytes 0 through 18: the ICCID number

import sys

import utils

class ProxyPkt:
    """Encapsulate a proxy packet"""
    
    # Pkt byte offsets
    SYNC_BYTE_0 = 0
    SYNC_BYTE_1 = 1
    SYNC_BYTE_2 = 2
    SYNC_BYTE_3 = 3
    LEN_LSB = 4
    LEN_MSB = 5
    TYPE = 6
    DATA = 7
    PROTOCOL_PKT_ID_Byte = DATA
    
    # Packet types
    PASSTHROUGH = 0
    ICCID_REQ = 1
    ICCID = 2
    PING = 3
    CONNECT = 4
    DISCONNECT = 5
    MIN_PKT_TYPE = 0
    MAX_PKT_TYPE = 5
    
    # Passthrough, Connect and Disconnect
    #   Packet Byte Offsets
    SRC_PORT_LSB = DATA + 0
    SRC_PORT_MSB = DATA + 1
    DEST_PORT_LSB = DATA + 2
    DEST_PORT_MSB = DATA + 3
    PASSTHROUGH_DATA = DATA + 4

    
    # Sync byte values
    SYNC_BYTE_0_VALUE = '\xAA'
    SYNC_BYTE_1_VALUE = '\x55'
    SYNC_BYTE_2_VALUE = '\x0F'
    SYNC_BYTE_3_VALUE = '\xF0'
    SYNC_CODE_STR = ''.join((SYNC_BYTE_0_VALUE,
                            SYNC_BYTE_1_VALUE,
                            SYNC_BYTE_2_VALUE,
                            SYNC_BYTE_3_VALUE))
        
    # Misc pkt attributes
    HDR_LEN = 7
    MIN_PKT_LEN = 9
    MAX_PKT_LEN = 512
    MAX_PASSTHROUGH_DATA_LEN = MAX_PKT_LEN - MIN_PKT_LEN - PASSTHROUGH_DATA
    CKSUM_LEN = 2
       
    def __init__(self, pkt_buf=''):
        """Create a proxy packet object
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
        parts.append(ProxyPkt.SYNC_CODE_STR)
        #print 'SYNC_CODE_STR is %s' % utils.bytes_to_hex(parts[0])
        if data is None:
            data_len = 0
        else:
            data_len = len(data)
        pkt_len = data_len + ProxyPkt.MIN_PKT_LEN
        len_lsb = pkt_len % 256
        len_msb = pkt_len / 256
        parts.append(chr(len_lsb))
        parts.append(chr(len_msb))
        parts.append(chr(type))
        if data_len > 0:
            parts.append(data)       
        cksum = (utils.str_sum(ProxyPkt.SYNC_CODE_STR) + \
                len_lsb + len_msb + type + \
                utils.str_sum(data)) & 0xFFFF        
        parts.append(chr(cksum % 256))
        parts.append(chr(cksum / 256))
        self._pkt_buf = ''.join(parts)
        return self._pkt_buf
        
    def get_pkt_buf(self):
        """Return a string containing the entire packet"""
        return self._pkt_buf
                
    def get_data(self):
        """Return the data field"""
        try:
            data_len = self.get_len() - ProxyPkt.MIN_PKT_LEN
            return self._pkt_buf[ProxyPkt.DATA:ProxyPkt.DATA + data_len]
        except IndexError:
            print 'IndexError in ProxyPkt.get_data()'
            return ''
            
    def get_data_len(self):
        """Return the number of data bytes"""
        return self.get_len() - ProxyPkt.MIN_PKT_LEN
    
    def get_len(self):
        """Return the ordinate of the length field"""
        try:
            return ord(self._pkt_buf[ProxyPkt.LEN_LSB]) + \
                        (ord(self._pkt_buf[ProxyPkt.LEN_MSB]) * 256)
        except IndexError:
            print 'IndexError in ProxyPkt.get_len()'
            return 0
    
    def get_type(self):
        """Return the ordinate of the type field"""
        try:
            return ord(self._pkt_buf[ProxyPkt.TYPE])
        except IndexError:
            print 'IndexError in ProxyPkt.get_type()'
            return 0
            
    def get_src_port(self):
        """Return the packet source port"""
        if (self.get_data_len() < 4):
            return 0
        else:
            return (ord(self._pkt_buf[ProxyPkt.SRC_PORT_MSB]) * 256) + \
                    ord(self._pkt_buf[ProxyPkt.SRC_PORT_LSB])       
                    
    def get_dest_port(self):
        """Return the packet destination port"""
        if (self.get_data_len() < 4):
            return 0
        else:
            return (ord(self._pkt_buf[ProxyPkt.DEST_PORT_MSB]) * 256) + \
                    ord(self._pkt_buf[ProxyPkt.DEST_PORT_LSB]) 
                    
    def get_passthrough_data_len(self):
        """Return the number of bytes of passthrough data
            not including src and dest port numbers"""
        len = self.get_data_len()
        if (self.get_data_len() < 4):
            return 0
        else:
            return len - 4      
                                      
    def cksum_is_valid(self):
        """Return True if the pkt checksum is valid"""
        try:
            pkt = self._pkt_buf
            data_len = self.get_len() - ProxyPkt.MIN_PKT_LEN
            calc_cksum = (ord(pkt[ProxyPkt.SYNC_BYTE_0]) + \
                    ord(pkt[ProxyPkt.SYNC_BYTE_1]) + \
                    ord(pkt[ProxyPkt.SYNC_BYTE_2]) + \
                    ord(pkt[ProxyPkt.SYNC_BYTE_3]) + \
                    ord(pkt[ProxyPkt.LEN_LSB]) + \
                    ord(pkt[ProxyPkt.LEN_MSB]) + \
                    ord(pkt[ProxyPkt.TYPE]) + \
                    utils.str_sum(pkt[ProxyPkt.DATA:ProxyPkt.DATA + data_len])) & 0xFFFF                              
            cksum_lsb = ord(pkt[ProxyPkt.DATA + data_len])       
            cksum_msb = ord(pkt[ProxyPkt.DATA + data_len + 1])       
            stored_cksum = cksum_lsb + (cksum_msb * 256)
        except IndexError:
            print 'IndexError in ProxyPkt.cksum_is_valid()'
            return False
        return calc_cksum == stored_cksum
        
    def str(self):
        """Return the pkt contents in printable form"""
        try:
            parts = []
            parts.append('ProxyPkt:\n')
            sync_code = self._pkt_buf[:ProxyPkt.SYNC_BYTE_3 + 1]
            parts.append('  sync code = %s' % utils.bytes_to_hex(sync_code))
            if sync_code == ProxyPkt.SYNC_CODE_STR:
                parts.append(' (valid)\n')
            else:
                parts.append(' (NOT valid)\n')
            parts.append('  length = %s' % str(self.get_len()))
            if len(self._pkt_buf) == self.get_len():
                parts.append(' (valid)\n')
            else:
                parts.append(' (NOT valid)\n')
            type = self.get_type()        
            parts.append('  type = %s' % str(type))
            if type == ProxyPkt.PASSTHROUGH:
                parts.append(' (passthrough)\n')
            elif type == ProxyPkt.ICCID_REQ:
                parts.append(' (ICCID request)\n')
            elif type == ProxyPkt.ICCID:
                parts.append(' (ICCID)\n')
            elif type == ProxyPkt.CONNECT:
                parts.append(' (CONNECT)\n')
            elif type == ProxyPkt.DISCONNECT:
                parts.append(' (DISCONNECT)\n')
            else:
                parts.append(' (unknown type)\n')
            
            parts.append('  data = %s\n' % utils.bytes_to_hex(self.get_data()))
            pkt_len = self.get_len()
            parts.append('  checksum = %s' % \
                    utils.bytes_to_hex(self._pkt_buf[pkt_len - 2:]))
            if (self.cksum_is_valid()):
                parts.append(' (valid)\n')
            else:
                parts.append(' (NOT valid)\n')
            return ''.join(parts)
        except IndexError:
            print 'IndexError in ProxyPkt.str()'
            return ''
    
def ICCIDReqPkt():
    """Return a string containing ICCID request proxy packet"""
    pkt = ProxyPkt()
    return pkt.build(ProxyPkt.ICCID_REQ)
        
    
def PingPkt():
    """Return a string containing ping proxy packet"""
    pkt = ProxyPkt()
    return pkt.build(ProxyPkt.PING)
    
        
def PassthroughPkt(src_port, dest_port, data):
    """Return a string containing a passthrough packet"""
    src_port_lsb = chr(src_port % 256)
    src_port_msb = chr(src_port / 256)
    dest_port_lsb = chr(dest_port % 256)
    dest_port_msb = chr(dest_port / 256)
    parts = []
    parts.append(src_port_lsb)
    parts.append(src_port_msb)
    parts.append(dest_port_lsb)
    parts.append(dest_port_msb)
    parts.append(data)
    pkt = ProxyPkt()
    return pkt.build(ProxyPkt.PASSTHROUGH, ''.join(parts))
    
def ConnectPkt(src_port, dest_port):
    """Return a string containing a CONNECT packet"""
    src_port_lsb = chr(src_port % 256)
    src_port_msb = chr(src_port / 256)
    dest_port_lsb = chr(dest_port % 256)
    dest_port_msb = chr(dest_port / 256)
    parts = []
    parts.append(src_port_lsb)
    parts.append(src_port_msb)
    parts.append(dest_port_lsb)
    parts.append(dest_port_msb)
    pkt = ProxyPkt()
    return pkt.build(ProxyPkt.CONNECT, ''.join(parts))
    
def DisconnectPkt(src_port, dest_port):
    """Return a string containing a DISCONNECT packet"""
    src_port_lsb = chr(src_port % 256)
    src_port_msb = chr(src_port / 256)
    dest_port_lsb = chr(dest_port % 256)
    dest_port_msb = chr(dest_port / 256)
    parts = []
    parts.append(src_port_lsb)
    parts.append(src_port_msb)
    parts.append(dest_port_lsb)
    parts.append(dest_port_msb)
    pkt = ProxyPkt()
    return pkt.build(ProxyPkt.DISCONNECT, ''.join(parts))                  
                     
   
       
if __name__ == '__main__':
    print 'Starting ProxyPkt test'
    pkt = ProxyPkt()
    
    pkt.build(ProxyPkt.ICCID_REQ)
    print "Building an ICCID_REQ packet: "
    print pkt.str()
        
    print "Building a passthrough packet with 7 data bytes: "
    pkt.build(ProxyPkt.PASSTHROUGH, data='\x01\x02\x03\x04\x05\x06\x07')
    print pkt.str()
        
    print 'Created a new packet from the previous packet'
    pkt = pkt.get_pkt_buf()[:]
    pkt = ProxyPkt(pkt)
    print pkt.str()
    
    print "Corrupting sync code"
    good_buf = pkt.get_pkt_buf()[:]
    bad_buf = good_buf[:]
    bad_buf = ''.join((bad_buf[:ProxyPkt.SYNC_BYTE_3], chr(0),
                    bad_buf[ProxyPkt.SYNC_BYTE_3 + 1:]))
    pkt = ProxyPkt(pkt_buf=bad_buf)
    print pkt.str()
    
    
    print "Corrupting length"
    bad_buf = good_buf[:]
    good_len_lsb = ord(bad_buf[ProxyPkt.LEN_LSB])
    bad_buf = ''.join((bad_buf[:ProxyPkt.LEN_LSB], chr(good_len_lsb - 1),
                    bad_buf[ProxyPkt.LEN_LSB + 1:]))    
    pkt = ProxyPkt(pkt_buf=bad_buf)
    print pkt.str()
    
    print "Building a passthrough packet, src = 5, dest = 6, data = 1,2,3"
    pkt_buf =  PassthroughPkt(5, 6, '\x01\x02\x03')
    pkt = ProxyPkt(pkt_buf)
    print pkt.str()
          
    print 'Exiting ProxyPkt test'
    
    
    

        
