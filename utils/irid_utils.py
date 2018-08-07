# Generally useful utilities

from datetime import datetime,timedelta

import utils


# Iridium Time Fix JAN2018
def get_iridium_time():
    """ Look for iridium system time in '/proc/iridium_time' """
    [iridium_time, stderr] = call_subprocess('cat /proc/iridium_time')
    if iridium_time == '-MSSTM: no network service':
        # In the event of an error getting iridium network time
        return 9999
    else:
        # We have a good time response
        epoch_counter = int(iridium_time.lstrip('-MSSTM: '))
        epoch_date = datetime(2014, 5, 11, 14, 23, 55, 00)
        time_diff = (epoch_counter * timedelta(milliseconds=90))
        sync_time = epoch_date + (epoch_counter * timedelta(milliseconds=90))
        if datetime.now() > sync_time:
            # System time ahead of Iridium time
            sync_age = datetime.now() - sync_time
        else:
            # System time behind Iridium time
            sync_age = sync_time - datetime.now()
        return int(sync_age.seconds)
