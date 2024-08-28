import os
import re
import csv

PAGE_SIZE = 4096
cold_dir = []
all_dir = []
cold_addr = {}
other_addr = {}
cold_offset = {}
other_offset = {}

path = input("input cold dir path, if done just press enter:\n")
while len(path) != 0:
    cold_dir.append(path)
    path = input("input cold dir path, if done just press enter:\n")
path = input("input all dir path, if done just press enter:\n")
while len(path) != 0:
    cold_dir.append(path)
    path = input("input all dir path, if done just press enter:\n")

for path in cold_dir:
    all_data = os.listdir(path)
    for data in all_data:
        if re.search(r'all_obj', data) is not None:
            output = data.split("_")
            cold_addr[output[1]] = True
for path in all_dir:
    all_data = os.listdir(path)
    for data in all_data:
        if re.search(r'all_obj', data) is not None:
            output = data.split("_")
            if cold_addr.get(output[1]) is None:
                other_addr[output[1]] = True

for addr in cold_addr:
    offset = int(addr, 16) // PAGE_SIZE
    cold_offset[offset] = True
errorflag = False
for addr in other_addr:
    offset = addr // PAGE_SIZE
    if cold_offset.get(offset):
        errorflag = True
        print("other addr :", addr, "\noffset :", offset)
if errorflag == False:
    print("ok")
