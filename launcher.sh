cd /

# Check if already running
result=`ps -aux | grep 'python3 Main.py' | grep -v grep`
if [ $? -eq 0 ]
    then
        echo "RedBot is Running."
    else
        echo "Starting RedBot..."
        cd /home/pi/Desktop/RedBot
        python3 Main.py
        cd /
fi
