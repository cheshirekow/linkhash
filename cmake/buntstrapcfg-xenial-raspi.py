from __future__ import unicode_literals

import os
from buntstrap import chroot
from buntstrap import config

architecture = "armhf"
suite = "xenial"
chroot_app = chroot.UchrootApp

apt_http_proxy = config.get_apt_cache_url()
apt_packages = [
    # "clang-6.0",
    # "clang-format-6.0",
    "build-essential",
    "cmake",
    "g++-6",
    "gcc-6",
    "gnuradio-dev",
    "libcurl4-openssl-dev",
    "libfuse-dev",
    "libgoogle-glog-dev",
    "libmagic-dev",
    "librtlsdr-dev",
    "libudev-dev",
    "libvulkan-dev",
    "libx11-xcb-dev",
    "ninja-build",
    "pkg-config",
    "python-pip",
]

apt_include_essential = True
apt_include_priorities = ["required"]

apt_sources = """
# NOTE(josh): these sources are used to bootstrap the rootfs and should be
# omitted from after initial package installation. You should not see this
# file on a live system.

#deb [arch={arch}] {ubuntu_url} {suite} main universe multiverse
#deb [arch={arch}] {ubuntu_url} {suite}-updates main universe multiverse
deb http://raspbian.raspberrypi.org/raspbian/ stretch main contrib non-free rpi
deb http://archive.raspberrypi.org/debian/ stretch main ui
""".format(arch=architecture,
           ubuntu_url=config.get_ubuntu_url(architecture),
           suite=suite)


apt_skip_update = False
apt_size_report = None
apt_clean = True
external_debs = []
dpkg_configure_retry_count = 1

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
]

qemu_binary = config.default_qemu_binary(architecture)
