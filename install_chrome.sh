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

# 获取Chrome版本
CHROME_VERSION=$(google-chrome-stable --version | awk '{print $3}' | cut -d. -f1)
echo "Chrome version: $CHROME_VERSION"

# 下载对应版本的ChromeDriver
echo "Downloading ChromeDriver..."
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION} -O chrome_version
CHROMEDRIVER_VERSION=$(cat chrome_version)
rm chrome_version

wget https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
rm chromedriver_linux64.zip

# 移动ChromeDriver到系统目录
sudo mv chromedriver /usr/bin/
sudo chown root:root /usr/bin/chromedriver
sudo chmod +x /usr/bin/chromedriver

# 创建虚拟显示
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# 检查安装
echo "Checking installations..."
echo "Chrome version:"
google-chrome-stable --version
echo "ChromeDriver version:"
chromedriver --version

echo "Chrome and ChromeDriver installation completed!"

# 显示安装位置
which google-chrome-stable
which chromedriver 