#!/bin/sh
# Script: Start up the Iridium comm watchdog daemon at boot time.
#   Never stop it.

start() {
    export PATH="./:/aal-pip/field/bin:$PATH"
    export PYTHONPATH="./:/aal-pip/field/bin:$PYTHONPATH"
    cd /aal-pip/field/bin
    comm-watchdog-daemon.py
}

stop() {
    echo "not stopping comm-watchdog"
}

case "$1" in
  start)
    start
        ;;
  stop)
    stop
        ;;
  restart)
        stop
        start
        ;;
  *)
        echo "Usage: $0 {start | stop | restart}"
        exit 1
        ;;
esac

exit 0
