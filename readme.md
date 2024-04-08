Start drcachesim
===
1. download and compile Dynamorio
    - source : https://dynamorio.org/page_building.html
    
    ```bash
    sudo apt-get install cmake g++ g++-multilib doxygen git zlib1g-dev libunwind-dev libsnappy-dev liblz4-dev

    # in malloc_project 
    mkdir ../mydynamorio && cd ../mydynamorio

    git clone --recurse-submodules -j4 https://github.com/DynamoRIO/dynamorio.git

    cd dynamorio && mkdir build && cd build

    cmake ..

    # Future modifications to Dynamorio only need to use this command
    make -j
    ```
2. download necessary package in pytohn for ./drcachesim
    ```bash
    sudo apt install pip
    
    # in malloc_project
    pip install -r requirements.txt
    ```