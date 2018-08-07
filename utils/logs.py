#!/usr/bin/env python

# Opens a log file in a standardized format

import logging
import logging.handlers

import utils

def open(name, dir, level, file_max_bytes=50000, num_backup_files=1):
    """
    Open a log and return it
    """
    # Create the log directory if it doesn't exist
    abs_dir = utils.expand_user_path(dir)
    utils.make_dirs(abs_dir)
    
    maxbytes = file_max_bytes
    backup   = num_backup_files
    msgfmt   = '[%(asctime)s %(levelname)7s] %(name)s: %(message)s'
    datefmt  = '%Y-%m-%d %H:%M:%S'    
    log      = logging.getLogger(name)
    handler  = logging.handlers.RotatingFileHandler("".join((abs_dir, '/', name, '.log')),
                        'a', maxbytes, backup)
    formatter = logging.Formatter(msgfmt, datefmt)    
    handler.setFormatter(formatter)
    log.addHandler(handler)  
    log.level = level
    return log
    
        
def _runTest():
    """Test the module"""
    print 'Testing logs.py'
    print 'Opening the log file'
    log = open('test_log', '.', logging.DEBUG)
    log.debug('First message')
    log.debug('Second message')
    log.debug('Third message')
    print 'Wrote three messages to test_log'
    print 'Closing all logs for this process'
    print 'Please examine the test_log.log file'
    # no close required for logging

if __name__ == '__main__':
    _runTest()
