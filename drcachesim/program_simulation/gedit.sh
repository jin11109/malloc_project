#!/bin/bash

sleep 5

end_time=$((1200))

while [ $SECONDS -lt $end_time ]; do
    xdotool type "Here is some example text for gedit. Let's add some operations to it."
    xdotool key Return
    sleep 2
    
    xdotool key Left Left Left Left Left
    sleep 2
    xdotool keydown shift
    xdotool key --delay 100 Left Left Left
    xdotool keyup shift
    sleep 1
    xdotool key ctrl+c
    sleep 1 for gedit. Le
    
    xdotool key Right
    xdotool key Return
    sleep 1
    xdotool key ctrl+v
    xdotool key Return
    sleep 2

    xdotool key Left Left
    xdotool key BackSpace
    sleep 1

    xdotool type "Adding some additional lines and content here."
    xdotool key Return
    sleep 2

    xdotool key Up
    xdotool key Home
    sleep 2
    xdotool keydown shift
    sleep 1
    xdotool key --delay 100 Right Right Right Right 
    xdotool keyup shift
    sleep 1
    xdotool key ctrl+x
    sleep 1
    xdotool key End
    xdotool key ctrl+v
    sleep 2

    sleep $((RANDOM % 3 + 1))
done

echo "done"