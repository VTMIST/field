#!/usr/bin/env python

###########################################################
#
#   datetime helper functions.
#
#   2004-12-27  Todd Valentic
#               Initial implementation
#
#   2005-04-07  Todd Valentic
#               Added parse_timedelta
#
###########################################################

import time

from datetime import datetime
from datetime import timedelta

def datetime_as_seconds(dt):

    # mktime takes a tuple in localtime. If we have tzinfo,
    # then compensate. First convert to UTC then to LT

    if dt.tzinfo:
        ut = dt-dt.utcoffset()
        lt = ut-timedelta(seconds=time.timezone)
        return time.mktime(lt.timetuple()) + lt.microsecond*1e-6 
    else:
        return time.mktime(dt.timetuple()) + dt.microsecond*1e-6 

def strptime(datestr,format,tzinfo=None):
    # Return a datetime object from strptime call
    tp = time.strptime(datestr,format)
    dt = datetime(tzinfo=tzinfo,*tp[0:6])
    return dt

def timedelta_as_seconds(td):      
    return td.days*3600*24 + td.seconds + td.microseconds*1e-6

def parse_timedelta(dtstr):

    days    = 0
    hours   = 0
    minutes = 0
    seconds = 0

    part = dtstr.split(',')

    if 'day' in part[0] or 'days' in part[0]:
        days = float(part[0].split('day')[0])
        if len(part)==1:
            return timedelta(days=days)
        part = part[1]
    else:
        part = part[0]

    times = part.split(':')

    if len(times)==0:       # 
        pass

    elif len(times)==1:     # 00
        seconds = float(times[0])

    elif len(times)==2:     # 00:00
        if times[0]:
            minutes = float(times[0])
        else:
            minutes = 0
        seconds = float(times[1])

    elif len(times)==3:     # 00:00:00
        hours   = float(times[0])
        minutes = float(times[1])
        seconds = float(times[2])
        
    return timedelta(days=days,hours=hours,minutes=minutes,seconds=seconds)

############################################################################

def __check_timedelta(line,target=None):
    
    try:
        dt = parse_timedelta(line)
    except:
        print '* Failed: %s (exception raised)' % line
        return

    if dt==target:
        print '  Passed: %s -> %s' % (line,dt)
    else:
        print '* Failed: %s -> got %s, expected %s' % (line,dt,target)

def __run_timedelta_tests():

    print 'These should all pass'

    __check_timedelta('0',timedelta())
    __check_timedelta('09',timedelta(seconds=9))
    __check_timedelta('2:23',timedelta(minutes=2,seconds=23))
    __check_timedelta('4:34',timedelta(minutes=4,seconds=34))
    __check_timedelta('43:23',timedelta(minutes=43,seconds=23))
    __check_timedelta('32:2',timedelta(minutes=32,seconds=2))
    __check_timedelta('23:32:43',timedelta(hours=23,minutes=32,seconds=43))
    __check_timedelta('1 day',timedelta(days=1))
    __check_timedelta('2 days',timedelta(days=2))
    __check_timedelta('2.5 days',timedelta(days=2,hours=12))
    __check_timedelta('1 day, 2',timedelta(days=1,seconds=2))
    __check_timedelta('1 day, 23:23',timedelta(days=1,minutes=23,seconds=23))
    __check_timedelta('1 day, 12:34:45',timedelta(days=1,hours=12,minutes=34,seconds=45))

    print
    print 'These should all fail'

    __check_timedelta('')
    __check_timedelta('chars')

if __name__ == '__main__':
    
    print 'Testing datetime_as_seconds'
    now = datetime.now()
    ts  = datetime_as_seconds(now)     
    print 'datetime.now() =',now
    print 'timestamp      =',ts
    print 'datetime  ctime=',now.ctime()
    print 'timestamp ctime=',time.ctime(ts)
    assert(now.ctime()==time.ctime(ts))
    print 'OK'

    print
    print 'Testing strptime'
    str = '2004-12-25 12:34:56'
    fmt = '%Y-%m-%d %H:%M:%S'
    dt  = strptime(str,fmt)
    print 'String   :',str
    print 'datetime :',dt
    assert(dt.strftime(fmt)==str)
    print 'OK'

    print
    print 'Testing timedelta_as_seconds'
    td   = timedelta(days=1,hours=2,minutes=3,seconds=4,microseconds=5)
    secs = timedelta_as_seconds(td)
    expected = 93784.000005
    print 'timedelta:',td
    print 'as seconds:',secs
    assert(secs==expected)
    print 'OK'

    import pytz
    utc = pytz.timezone('UTC')
    pst = pytz.timezone('US/Pacific')

    print 'datetime.now():',
    secs = datetime_as_seconds(datetime.now())
    print secs-time.time(), 
    print datetime.fromtimestamp(secs),
    print datetime.fromtimestamp(secs)

    print 'datetime.now(utc):',
    secs = datetime_as_seconds(datetime.now(utc))
    print secs-time.time(), 
    print datetime.fromtimestamp(secs),
    print datetime.fromtimestamp(secs,utc)

    print 'datetime.now(pst):',
    secs = datetime_as_seconds(datetime.now(pst))
    print secs-time.time(), 
    print datetime.fromtimestamp(secs),
    print datetime.fromtimestamp(secs,pst)

    print 'Testing parse_timedelta'
    __run_timedelta_tests()

