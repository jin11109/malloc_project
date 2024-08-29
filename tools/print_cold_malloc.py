import os
import re
import csv

path = input("screenlog path:\n")
addrs = {}
with open(path, 'r') as f:
    while 1:
        data = f.readline()
        if len(data) == 0:
            break
        if data[0 : 2] != "0x":
            continue
        if addrs.get(data) is None:
            addrs[data] = True
        else:
            continue

with open("addrs.txt", 'w') as f:
    for addr in addrs:
        f.write(addr)
