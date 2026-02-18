# -*- coding: utf-8 -*-
import logging
import undetected_chromedriver as uc

log = logging.getLogger(__name__)


def create_browser(headless: bool = True, retry: int = 2):
    """创建并返回 Chrome WebDriver
    
    Args:
        headless: 是否使用无头模式
        retry: 失败后重试次数
    """
    options = uc.ChromeOptions()

    base_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions",
    ]

    for arg in base_args:
        options.add_argument(arg)

    if headless:
        options.add_argument("--headless=new")

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
    )

    for attempt in range(retry + 1):
        try:
            # 自动使用系统 Chrome 版本匹配驱动
            driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
            driver.set_window_size(1920, 1080)

            # 反自动化基础伪装
            driver.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
            driver.execute_script("window.chrome={runtime:{}}")
            driver.execute_script("Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh']})")
            driver.execute_script("Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3]})")

            log.info("✅ 浏览器启动成功")
            return driver
            
        except Exception as e:
            if attempt < retry:
                log.warning(f"⚠️ 浏览器启动失败 (尝试 {attempt + 1}/{retry + 1})，正在重试...")
                # 清理可能存在的驱动缓存
                try:
                    import shutil
                    import os
                    cache_dir = os.path.expanduser("~/.local/share/undetected_chromedriver")
                    if os.path.exists(cache_dir):
                        log.info(f"🗑️ 清理驱动缓存: {cache_dir}")
                        shutil.rmtree(cache_dir, ignore_errors=True)
                except Exception:
                    pass
            else:
                log.error(f"❌ 浏览器启动失败: {e}")
                return None


def inject_cookies(driver, base_url: str, cookie_str: str, domain: str):
    """向浏览器注入 Cookie"""
    driver.get(base_url)

    for item in cookie_str.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue

        name, value = item.split("=", 1)
        try:
            driver.add_cookie({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
                "secure": True,
                "httpOnly": False
            })
        except Exception as e:
            log.warning(f"⚠️ Cookie 注入失败: {name} -> {e}")
