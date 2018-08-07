#!/bin/sh
#
# Enable the watchdog timer
# Uses the kernel ts72xx_wdt watchdog module

# Make sure the watchdog device exists.
[ -c /dev/watchdog ] || exit 0

start() {
    echo -n "Starting watchdog timer: "
    start-stop-daemon -S -q --exec /sbin/watchdog -- -T 8000 -t 4 /dev/watchdog
    echo "OK"
}

stop() {
    echo -n "Stopping watchdog timer: "
    start-stop-daemon -K -q --exec /sbin/watchdog
    echo "OK"
}

restart() {
    stop
    start
}

case $1 in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart|reload)
        restart
        ;;
    *)
        echo $"Usage: $0 {start|stop|restart}"
        exit 1
esac

exit $?

