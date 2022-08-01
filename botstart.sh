#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/usr/bot:/opt/root:/opt/lib:/opt/lib/python3.10:

PYTHON="/opt/bin/python3 /opt/usr/bot/notebot.py"

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

if notebot_status
then
    stop
    sleep 3		
    start
else		
    start
fi
