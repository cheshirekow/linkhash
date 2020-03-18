============================
Notes on current build setup
============================

Environment required to build
=============================

Ubuntu packages:

  * clang-6.0
  * clang-format-6.0
  * clang-tidy-6.0
  * cmake
  * g++-5-multilib
  * gcc-5-multilib
  * gnuradio-dev
  * libcurl4-openssl-dev
  * libfuse-dev
  * libgoogle-glog-dev
  * libmagic-dev
  * librtlsdr-dev
  * libudev-dev
  * libvulkan-dev
  * libx11-xcb-dev
  * ninja-build
  * nodejs
  * pkg-config
  * python-pip

Additional ubuntu packages:

  * qemu
  * qemu-user-static

Python packages:

  * pylint
  * yapf

For clang builds, install the following packages:

  * clang-6.0
  * clang-format-6.0
  * clang-tidy-6.0

and add symlinks to the environment to point `clang` `clang-format` and
`clang-tidy` to those versions.

The environment setup for `yapf` is a bit annoying. `yapf` will conform to
standards for whatever python it is run under. So we probably want to use it
with python3. There's a problem with ubuntu distributed packages are too old
to deal with modern features on pypi, so you'll need to do this:

```
python3 -m pip install --upgrade --user pip
# restore `pip` meaning `pip2`
python -m pip install --upgrade --user --force-reinstall pip
python3 -m pip install pylint yapf
```
It's important that these binaries in the environment point to the python3
version... as it is impossible to get consistent lint/formatting for both
languages.

Install glslangValidator
========================

sudo add-apt-repository ppa:josh-bialkowski/glslang
sudo apt-get update
sudo apt install glslang

Install Bazel
=============

Step 1: Install the JDK
Install JDK 8:

::
    sudo apt-get install openjdk-8-jdk

On Ubuntu 14.04 LTS you must use a PPA:

::
    sudo add-apt-repository ppa:webupd8team/java
    sudo apt-get update && sudo apt-get install oracle-java8-installer

Step 2: Add Bazel distribution URI as a package source
Note: This is a one-time setup step.

::
    echo "deb [arch=amd64] http://storage.googleapis.com/bazel-apt stable jdk1.8" | sudo tee /etc/apt/sources.list.d/bazel.list
    curl https://bazel.build/bazel-release.pub.gpg | sudo apt-key add -

If you want to install the testing version of Bazel, replace stable with
testing.

Step 3: Install and update Bazel

::
    sudo apt-get update && sudo apt-get install bazel

Notes on 18.04
==============

The libudev package in 18.04 does not appear to actually contain libudev.
You might be able to download and install it manually from:
wget http://mirrors.kernel.org/ubuntu/pool/main/u/udev/libudev0_175-0ubuntu9_amd64.deb


Notes on container build
========================

Creating the container::

    mkdir ~/wheelhouse
    buntstrap -c cmake/buntstrapcfg-amd64.py ${PWD}/.build/amd64-rootfs
    mkdir /tmp/rootfs/src
    mkdir /tmp/rootfs/build
    mksquashfs /tmp/rootfs/ .build/container.squash
    mkdir .build/out
    sudo mount -t squashfs .build/container.squash /mnt/
    sudo mount -o bind . /mnt/src
    sudo mount -o bind .build/out /mnt/build
    sudo mount -t proc proc /mnt/proc
    sudo chroot --userspec josh:josh /mnt/

    I have no name!@cookie:/build$ CC=/usr/bin/clang-6.0 CXX=/usr/bin/clang++-6.0 cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=On -G Ninja /src

Raspberry Pi build container::

    buntstrap -c cmake/buntstrapcfg-armhf.py ${PWD}/.build/armhf-rootfs
    cd .build
    mkdir armhf-build
    mkdir armhf-rootfs/src
    mkdir armhf-rootfs/build
    mount -o bind /dev armhf-rootfs/dev
    mount -o bind /home/josh/tangentsky armhf-rootfs/src
    mount -o bind armhf-build armhf-rootfs/build
    uchroot armhf-rootfs
    cd build
    cmake ../src -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_TYPE=Release -G Ninja
    ninja grfh-receive


Notes on current tangentbuild
=============================

Currently can build raspi rootfs with::

    BUILD=/home/josh/codes/tangentsky/.build
    $ python -Bm tangentbuild build BuntstrapRootfs \
      cmake/buntstrapcfg-raspi.py \
      $BUILD/rootfs/raspi-stage \
      $BUILD/rootfs/raspi.manifest \
      $BUILD/rootfs/raspi.squash

Build Matrix
============

::

    suite: ["xenial", "bionic", "windows", "mac", "none"]
    arch: ["amd64", "armhf", "arm64"]
    compiler: {
      "clang": ("3.8", "4", "5", "6"),
      "gcc": ("4.9", "5.4", "6.0")
    }
    build-type: ["release", "relwithdebinfo", "debug"]
    c++ standard: ["c++11", "c++14", "c++20"]
    build-tool: ["bazel", "cmake"]

This alone yields: 2 * 3 * 6 * 3 * 3 = 324. Obviously, we don't want to build
all of those all the time. But maybe we do want to build all of them every once
in a while.
