#!/bin/bash
# Chrome/Chromium 安装和检查脚本

echo "🔍 检查当前 Chrome/Chromium 安装情况..."
echo ""

# 检查 Google Chrome
if command -v google-chrome &> /dev/null; then
    VERSION=$(google-chrome --version 2>/dev/null)
    echo "✅ 已安装 Google Chrome: $VERSION"
    CHROME_INSTALLED=true
elif command -v google-chrome-stable &> /dev/null; then
    VERSION=$(google-chrome-stable --version 2>/dev/null)
    echo "✅ 已安装 Google Chrome Stable: $VERSION"
    CHROME_INSTALLED=true
fi

# 检查 Chromium
if command -v chromium &> /dev/null; then
    VERSION=$(chromium --version 2>/dev/null)
    echo "✅ 已安装 Chromium: $VERSION"
    CHROMIUM_INSTALLED=true
elif command -v chromium-browser &> /dev/null; then
    VERSION=$(chromium-browser --version 2>/dev/null)
    echo "✅ 已安装 Chromium Browser: $VERSION"
    CHROMIUM_INSTALLED=true
fi

if [ -z "$CHROME_INSTALLED" ] && [ -z "$CHROMIUM_INSTALLED" ]; then
    echo "❌ 未找到 Chrome 或 Chromium"
    echo ""
    echo "📦 正在安装 Google Chrome..."
    echo ""
    
    # 下载并安装 Google Chrome
    cd /tmp
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    
    if [ $? -eq 0 ]; then
        echo "📦 安装 Google Chrome..."
        sudo dpkg -i google-chrome-stable_current_amd64.deb
        
        # 修复依赖问题
        sudo apt-get install -f -y
        
        # 清理
        rm google-chrome-stable_current_amd64.deb
        
        echo ""
        echo "✅ Google Chrome 安装完成！"
        google-chrome --version
    else
        echo "❌ 下载失败，请检查网络连接"
        exit 1
    fi
else
    echo ""
    echo "✅ Chrome/Chromium 已安装，无需额外操作"
fi

echo ""
echo "🗑️ 清理驱动缓存..."
CACHE_DIR="$HOME/.local/share/undetected_chromedriver"
if [ -d "$CACHE_DIR" ]; then
    rm -rf "$CACHE_DIR"
    echo "✅ 已清理驱动缓存"
else
    echo "ℹ️  无需清理（缓存不存在）"
fi

echo ""
echo "🧪 测试脚本运行..."
cd ~/nodeloc-auto-signin
python3 main.py

echo ""
echo "✅ 完成！"
