# Implements a mutual exclusion lock (mutex)

import os
import errno

class LockFile:

    """Mutual exclusion lockfile class
    
    Methods:
    acquire - Take possession of the mutex, non-blocking
    release - Relinquish possession the mutex
    isLocked - Return True if the mutex is owned by any process
    ownlock - Return True if the mutex is owned by this process
    
    """

    def __init__(self, path, log):
        self.path   = path
        self.pid    = os.getpid()
        self.log    = log

    def acquire(self):
        """
        Acquire the lock file
        
        Returns True or False
        """
        self.log.debug("Trying to acquire lock")

        retry=0
        maxRetries=10

        while True:

            try:
                fd = os.open(self.path,os.O_EXCL | os.O_RDWR | os.O_CREAT)
                # we created the file, so we own it
                self.log.debug("  - lock file created")
                break
            except OSError,e:
                if e.errno != errno.EEXIST:
                    self.log.exception("Error creating lock!")
                    # should not occur
                    raise

                self.log.debug("  - lock file already exists")

                try:
                    # the lock file exists, try to read the pid to see if it is ours
                    f = open(self.path,'r')
                    self.log.debug("  - opened lock file")
                except OSERROR, e:
                    self.log.exception("Failed to open lock file!")
                    if e.errno != errno.ENOENT:
                        self.log.error("not ENOENT, aborting")
                        raise
                    # The file went away, try again
                    if retry<maxRetries:
                        retry+=1
                        self.log.debug("  - trying again, retry: %d" % retry)
                        time.sleep(1)
                        continue
                    else:
                        self.log.error("  - max retries, return false")
                        return False

                # Check if the pid is ours

                self.log.debug("  - checking pid")

                pid = int(f.readline())
                f.close()

                self.log.debug("  - pid=%d, ours=%d" % (pid,self.pid))

                if pid==self.pid:
                    # it's ours, we are done
                    self.log.debug("  - we own this file, return true")
                    return True

                self.log.debug("  - not ours")

                # It's not ours, see if the PID exists
                try:
                    os.kill(pid,0)
                    self.log.error("  - owner pid still exists, return false")
                    # PID is still active, this is somebody's lock file
                    return False
                except OSError,e:
                    if e.errno!=errno.ESRCH:
                        self.log.error("  - owner still exists, return false")
                        # PID is still active, this is somebody's lock file
                        return False

                self.log.debug("  - owner is not running anymore")

                # The original process is gone. Try to remove.
                try:
                    os.remove(self.path)
                    time.sleep(5)
                    # It worked, must have been ours. Try again.
                    self.log.debug("  - removed lock file. try again")
                    continue
                except:
                    self.log.error("  - failed to remove. return false")
                    return False

        # If we get here, we have the lock file. Record our PID.

        self.log.debug("  - record pid in file")

        fh = os.fdopen(fd,'w')
        fh.write('%10d\n' % self.pid)
        fh.close()

        self.log.debug("  - lock acquired!")

        return True

    def release(self):
        """Release the lock file"""
        if self.ownlock():
            os.unlink(self.path)

    def _readlock(self):
        try:
            return int(open(self.path).readline())
        except:
            return 8**10

    def isLocked(self):
        """Return True if file is locked"""
        try:
            pid = self._readlock()
            os.kill(pid,0)
            return True
        except:
            return False

    def ownlock(self):
        """Return true if this process owns the lock"""
        pid = self._readlock()
        return pid==self.pid

    def __del__(self):
        self.release()
