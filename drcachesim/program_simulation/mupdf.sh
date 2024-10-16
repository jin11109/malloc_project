#!/bin/bash

sleep 10
end_time=$((1200))

while [ $SECONDS -lt $end_time ]; do
    xdotool click 5
    sleep 80
    xdotool click 5
    sleep 80
    xdotool click 5
    sleep 80
    xdotool click 4
    sleep 40
    sleep $((RANDOM % 3 + 1))
done
