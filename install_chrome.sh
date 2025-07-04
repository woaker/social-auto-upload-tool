#!/bin/bash

echo "Installing Chrome and dependencies for Amazon Linux 2..."

# 安装基础依赖
sudo yum update -y
sudo yum install -y wget unzip libX11 libXcomposite libXcursor libXdamage libXext libXi libXtst cups-libs libXScrnSaver libXrandr alsa-lib pango at-spi2-atk gtk3 xorg-x11-server-Xvfb

# 下载并安装Chrome
echo "Downloading Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm

echo "Installing Chrome..."
sudo yum install -y ./google-chrome-stable_current_x86_64.rpm

# 清理下载文件
rm -f google-chrome-stable_current_x86_64.rpm

# 创建虚拟显示
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# 检查Chrome版本
echo "Checking Chrome version..."
google-chrome-stable --version

echo "Chrome installation completed!"

# 显示安装位置
which google-chrome-stable 