#!/bin/bash

# 添加Chrome仓库
sudo curl -o /etc/yum.repos.d/google-chrome.repo https://dl.google.com/linux/chrome/rpm/google-chrome.repo

# 安装Chrome浏览器
sudo yum install -y google-chrome-stable

# 安装Chrome驱动依赖
sudo yum install -y xorg-x11-server-Xvfb

# 创建虚拟显示
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# 检查Chrome版本
google-chrome --version

echo "Chrome installation completed!" 