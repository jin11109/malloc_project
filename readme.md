Start drcachesim
===
1. download and compile Dynamorio
    - source : https://dynamorio.org/page_building.html
    
    ```bash
    sudo apt-get install cmake g++ g++-multilib doxygen git zlib1g-dev libunwind-dev libsnappy-dev liblz4-dev

    # in malloc_project 
    mkdir ../mydynamorio && cd ../mydynamorio
    
    git clone --recurse-submodules -j4 https://github.com/jin11109/dynamorio.git
    
    cd ./dynamorio
    git branch -r | grep -v '\->' | while read remote; do git branch --track "${remote#origin/}" "$remote"; done

    # for online output
    git checkout online
    # for offline 
    git checkline offline

    mkdir build && cd build

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

3. make sure system can open enough files (We use 32768) 
    - test how many files can open
        ```bash
        ulimit -a
        ```
    - if there isn't enough

        ```bash
        sudo nano /etc/security/limits.conf
        ```
        add below texts into limits.conf
        ```text
        * soft nofile 32768
        * hard nofile 32768
        ```
        ```bash
        reboot
        ```
        ```
        ulimit -n 32768
        ```
