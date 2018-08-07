#! /usr/bin/python

# Test program that eats up CPU time.
# Used only for testing the CPU Load Watchdog.

import sys
import utils
import global_config 

                
def _run_time_waster():
    print('')
    print('****** Starting time-waster ******')
    
    while True:
        try:
            for i in range (0, 30000):
                s = "a;djfalfjasdl;fajdl;fjasdf  alkdfja ;ldfjal;sdfj  jad;lfjasd;lfjaksdflkjd"
                s = "qoroqerueouewqroiq nqeoiruq proqieu ruqoweruq eporuuqeropque r uuqoperuqowie"
                s = "a;djfalfjasdl;fajdl;fjasdf  alkdfja ;ldfjal;sdfj  jad;lfjasd;lfjaksdflkjd"
                s = "qoroqerueouewqroiq nqeoiruq proqieu ruqoweruq eporuuqeropque r uuqoperuqowie"
                s = "a;djfalfjasdl;fajdl;fjasdf  alkdfja ;ldfjal;sdfj  jad;lfjasd;lfjaksdflkjd"
                s = "qoroqerueouewqroiq nqeoiruq proqieu ruqoweruq eporuuqeropque r uuqoperuqowie"
        except KeyboardInterrupt:
            print('Got SIGINT (shutting down)')
            break
        except:
            print('Got an unexpected exception')
            sys.exit(1)
                   
    print('****** Exiting time-waster ******')
    
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    _run_time_waster()

