
# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
echo 400000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null
# 39750

# compile preload program
gcc -O0 ./test_perf.c -o ./test_perf -lm

./test_perf

perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log

# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
