About This Project
===

This project use three tools, which are *Perf*, *Dynamorio* and *Pintool*, to profile allocs. After getting and processing data, it will produce some pictures to display what we interesting in.

**Introduce drcachesim:** drcachesim is one of tools in opensource ,*Dynamorio* , and aims to simulate the behavior of caches.

Build drcachesim
===


**Our Environment**: 
- OS: Ubuntu 20.04 LTS
- In `uname -a` open files: 32768
- RAM: 16GB
- SWAP: 128GB
----------------------------------------------------------------
1. **Download and compile Dynamorio**
    - source : https://dynamorio.org/page_building.html
    
    ```bash
    sudo apt-get install cmake g++ g++-multilib doxygen git zlib1g-dev libunwind-dev libsnappy-dev liblz4-dev
    
    # in malloc_project folder
    mkdir ../mydynamorio && cd ../mydynamorio
    
    git clone --recurse-submodules -j4 https://github.com/jin11109/dynamorio.git
    
    cd ./dynamorio
    git branch -r | grep -v '\->' | while read remote; do git branch --track "${remote#origin/}" "$remote"; done

    # for online output
    # we now mainly use this part
    git checkout online
    # for offline 
    git checkout offline

    mkdir build && cd build

    cmake ..

    # Future modifications to Dynamorio only need to use this command
    make -j
    ```

2. **Download necessary packages for pytohn**
    ```bash
    sudo apt install pip
    
    # in malloc_project folder
    pip install -r requirements.txt
    ```

Quickly Start
===
1. **Enter drcachesim folder to start with this tool.**
    ```bash
    # in malloc_project folder
    cd drcachesim
    ```
2. **Use script to start the program you want to profile.**
    ```bash
    ./demo.sh program
    ```
3. **After above steps you will get three new folders, *data*, *result* and *result_picture*, in the drcachesim folder.**