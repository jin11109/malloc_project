About This Project
===
This project is currently divided into two main phases. First, [build the data collection framework](/readme.md#1-ｄata-collection-framework) with *drcachesim in DynamoRIO*, followed by an observation and synthesis of the behavior of dynamic memory objects based on the collected data. And, a determination formula is then proposed to classify whether a memory allocator caller is "cold". Second, Based on the classification results, [two identical dynamic memory allocators, ptmalloc2,](/readme.md#2-ｔwo-identical-allocators-framework) are used to simulate the outcomes of classification of ma-callers.

### 1. **Ｄata collection framework**：

![alt text](/doc/image/data_collection_framework.png)

We have used three tools, which are *Perf*, *Dynamorio* and *Pintool*, to profile memory allocator callers (ma-callers). But now we finally used *drcachesim* in *DynamoRIO* as the picture showing. After getting and processing data, it will produce some pictures to display what we interesting in. For a more detailed explanation, please refer to [Ｄata collection framework with drcachesim](/drcachesim/readme.md). If you would like to learn more about tools we are no longer using, please refer to [DynamoRIO](/DynamoRIO/readme.md), [Pintools](/pintools/readme.md) and [perf](/perf/readme.md).

### 2. **Ｔwo identical allocators framework**：

![alt text](/doc/image/two_identical_allocators_framework.png)

In this section, we will experiment with the benefits of separating the memory allocator callers (ma-caller) based on the experimental framework shown in the image. For a more detailed explanation, please refer to [Ｔwo  identical allocators framework](/two_mallocs/readme.md). If you would like to learn more about the *ptmalloc2* we are using, please refer to [ptmalloc2](/two_mallocs/ptmalloc2_with_cold/readme.md).

**Introduce drcachesim:** drcachesim is one of tools in opensource ,*Dynamorio* , and aims to simulate the behavior of caches.

Quick Start
===
#### **Our Environment**: 
- OS: Ubuntu 20.04 LTS
- In `uname -a` open files: 32768
- RAM: 16GB
- SWAP: 128GB
----------------------------------------------------------------
### 1. Ｄata collection framework
#### 1.1 Download and compile Dynamorio
- source : https://dynamorio.org/page_building.html
    
```bash
sudo apt-get install cmake g++ g++-multilib doxygen git zlib1g-dev libunwind-dev libsnappy-dev liblz4-dev

# in malloc_project(root) folder
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

#### 1.2. Download necessary packages for pytohn
```bash
sudo apt install pip

# in malloc_project(root) folder
pip install -r requirements.txt
```

#### 1.3 Enter drcachesim folder to start data collection framework.
```bash
# in malloc_project(root) folder
cd drcachesim
./demo.sh program
```
#### 1.4 After above steps you will get three new folders, *data*, *result* and *result_picture*, in the drcachesim folder.
----------------------------------------------------------------
### 2. Ｄata collection framework
#### 2.1 Chnage the branch and compile Dynamorio
```bash
# in mydynamorio/dynamorio/build
git checkout two-mallocs
make -j
```
#### 2.2 Enter drcachesim folder to start data collection framework.
```bash
# in malloc_project(root) folder
cd two_mallocs
./demo.sh program
```
#### 2.3 After above steps you will get three new folders, *data*, *result* and *result_picture*, in the two_mallocs folder.