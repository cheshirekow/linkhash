from __future__ import unicode_literals

import os
from buntstrap import chroot
from buntstrap import config

architecture = "amd64"
suite = "xenial"
chroot_app = chroot.UchrootApp

apt_http_proxy = config.get_apt_cache_url()
apt_packages = [
    "bazel",
    "clang-3.8",
    "clang-6.0",
    "clang-format-6.0",
    "clang-tidy-6.0",
    "cmake",
    "g++-5-multilib",
    "gcc-5-multilib",
    "glslang",
    "gnuradio-dev",
    "libcurl4-openssl-dev",
    "libeigen3-dev",
    "libenchant-dev",  # required by sphinx
    "libfontconfig1-dev",
    "libfreetype6-dev",
    "libfuse-dev",
    "libgnuradio-osmosdr0.1.4",
    "libgoogle-glog-dev",
    "libmagic-dev",
    "librtlsdr-dev",
    "libudev-dev",
    "libvulkan-dev",
    "libx11-xcb-dev",
    "ninja-build",
    "nodejs",
    "openjdk-8-jdk",
    "pkg-config",
    "python-pip",
    "python3-minimal",
    "python3-pip",
    "libpython3.5-stdlib",
    # required for buildslave, not necessarily for build environment
    "apt",
    "fuse",
    "git",
    "libpython3-dev",  # required to build twistd
    "openssh-client",
]

apt_include_essential = True
apt_include_priorities = ["required"]

apt_sources = """
# NOTE(josh): these sources are used to bootstrap the rootfs and should be
# omitted from after initial package installation. You should not see this
# file on a live system.

deb [arch={arch}] {ubuntu_url} {suite} main universe multiverse
deb [arch={arch}] {ubuntu_url} {suite}-updates main universe multiverse
deb [arch={arch}] {nodesource_url} {suite} main
deb [arch={arch}] {cuda_url}/ubuntu1604/x86_64 /
deb [arch={arch}] {ppa_url}/josh-bialkowski/glslang/ubuntu {suite} main
deb [arch={arch}] {ppa_url}/graphics-drivers/ppa/ubuntu {suite} main
deb [arch={arch}] http://storage.googleapis.com/bazel-apt stable jdk1.8
""".format(
    arch=architecture,
    ubuntu_url=config.get_ubuntu_url(architecture),
    suite=suite,
    nodesource_url="https://deb.nodesource.com/node_8.x",
    cuda_url="http://developer.download.nvidia.com/compute/cuda/repos",
    ppa_url="http://ppa.launchpad.net")

apt_skip_update = False
apt_size_report = None
apt_clean = True
external_debs = []
dpkg_configure_retry_count = 1

binds = [
    "/dev/urandom",
    "/etc/resolv.conf",
    "/proc",  # needed to install java
]

pip_wheelhouse = os.path.expanduser("~/wheelhouse")
pip_packages = [
    "autopep8",
    'cpplint',
    'file-magic',
    'flask',
    'oauth2client',
    'pygerrit2',
    'pylint',
    'recommonmark',
    'sphinx',
    'sqlalchemy',
    'yapf',
]

node_packages = [
    "eslint"
]

qemu_binary = config.default_qemu_binary(architecture)
