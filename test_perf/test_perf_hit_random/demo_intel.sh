
# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null
# 39750

# compile program
gcc -O3 -g ./test_perf_hit_random.c -o ./test_perf_hit_random

#perf stat -e instructions ./test_perf_hit_random
perf record -e mem-stores:ppp,mem-loads:ppp -F max --running-time --data ./test_perf_hit_random

perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log
python3 ./filter.py
python3 ./show.py

# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
