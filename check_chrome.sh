#!/bin/bash
# Chrome 和驱动版本检查与修复脚本

echo "🔍 检查 Chrome 浏览器版本..."

# 检测 Chrome 版本
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
    echo "✅ Chrome 版本: $CHROME_VERSION"
elif command -v chromium &> /dev/null; then
    CHROME_VERSION=$(chromium --version | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
    echo "✅ Chromium 版本: $CHROME_VERSION"
elif command -v chromium-browser &> /dev/null; then
    CHROME_VERSION=$(chromium-browser --version | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
    echo "✅ Chromium 版本: $CHROME_VERSION"
else
    echo "❌ 未找到 Chrome/Chromium 浏览器"
    echo "请安装 Chrome 或 Chromium："
    echo "  Ubuntu/Debian: sudo apt install chromium-browser"
    echo "  CentOS/RHEL:   sudo yum install chromium"
    exit 1
fi

# 检查 undetected_chromedriver 缓存
CACHE_DIR="$HOME/.local/share/undetected_chromedriver"
if [ -d "$CACHE_DIR" ]; then
    echo "📁 驱动缓存目录: $CACHE_DIR"
    echo "📝 缓存内容:"
    ls -lh "$CACHE_DIR" 2>/dev/null || echo "  (空)"
    
    echo ""
    read -p "是否清理驱动缓存？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CACHE_DIR"
        echo "✅ 已清理驱动缓存"
    fi
else
    echo "ℹ️  驱动缓存目录不存在（首次运行会自动创建）"
fi

echo ""
echo "🧪 测试浏览器启动..."
python3 -c "
import undetected_chromedriver as uc
try:
    print('🔄 正在启动浏览器...')
    driver = uc.Chrome(headless=True, version_main=None)
    print('✅ 浏览器启动成功！')
    driver.quit()
except Exception as e:
    print(f'❌ 浏览器启动失败: {e}')
"

echo ""
echo "✅ 检查完成！"
echo ""
echo "💡 常见问题解决："
echo "  1. 版本不匹配 → 清理缓存后重新运行"
echo "  2. 权限问题 → 确保有执行权限: chmod +x check_chrome.sh"
echo "  3. Chrome 未安装 → 安装 Chrome 或 Chromium"
