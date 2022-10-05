#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/usr/bot:/opt/root:/opt/lib:/opt/lib/python3.10:

PYTHON="/opt/bin/python3 /opt/usr/family_bot/startbot.py"

notebot_status ()
{
	ps | grep python3 | grep -v grep
}

start()
{
	$PYTHON &
}

stop()
{
	killall python3
}

sleep 10

case "$1" in
	start)
		if notebot_status
		then
			echo notebot already running
		else
			start
		fi
		;;
	stop)
		if notebot_status
		then
			stop
		else
			echo notebot is not running
		fi
		;;
	status)
		if notebot_status
		then
			echo notebot already running
		else
			echo notebot is not running
		fi
		;;

	restart)
		stop
		sleep 3
		start
		;;
	*)
		echo "Usage: $0 {start|stop|restart|status}"
		;;
esac
