#!/bin/sh
# Script: Start up aal-pip at boot time.
#   Stop aal-pip at shutdown time.

start() {
    export PATH="./:/aal-pip/field/bin:$PATH"
    export PYTHONPATH="./:/aal-pip/field/bin:$PYTHONPATH"
    cd /aal-pip/field/bin
    rm -f /var/log/connect_time
    rm -f /var/log/disconnect_time
    rm -f /var/log/keep_alive
    /aal-pip/field/bin/start_all.py
}

stop() {
    /aal-pip/field/bin/stop_all.py
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
