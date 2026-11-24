#!/usr/bin/env bash
set -e
sudo apt-get update
sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
  zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev libltdl-dev
python3 -m pip install --upgrade pip
pip install buildozer cython==0.29.36
buildozer -v android debug
