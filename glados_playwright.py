import asyncio
import json
import os
import sys
import logging
from datetime import datetime
import yaml
from playwright.async_api import async_playwright
import requests

# -------------------------------------------------------------------------------------------
# 日志配置
# -------------------------------------------------------------------------------------------
def setup_logger():
    """配置日志系统"""
    # 创建 logs 目录
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 生成日志文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'checkin_{timestamp}.log')

    # 配置日志
    logger = logging.getLogger('GLaDOS')
    logger.setLevel(logging.INFO)

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 格式化
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建全局 logger
logger = logging.getLogger('GLaDOS')

# -------------------------------------------------------------------------------------------
# 加载配置文件
# -------------------------------------------------------------------------------------------
def load_config():
    """加载配置文件，优先从 yaml 文件读取，环境变量作为备选"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')

    # 如果存在配置文件，从 yaml 读取
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # 否则使用环境变量
    cookie_str = os.environ.get("GLADOS_COOKIE", "")
    if not cookie_str:
        logger.info('未找到配置文件 config.yaml 或 GLADOS_COOKIE 环境变量')
        exit(0)

    # 将环境变量的 cookie 转换为配置格式
    cookies = [{"cookie": c} for c in cookie_str.split("&")]
    return {
        "pushplus_token": os.environ.get("PUSHPLUS_TOKEN", ""),
        "cookies": cookies
    }


async def checkin_with_playwright(cookie_str):
    """使用 Playwright 执行签到"""
    async with async_playwright() as p:
        # 启动浏览器（使用 headless 模式）
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            proxy={"server": "http://127.0.0.1:7890"},  # Clash 代理
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 设置 Cookie
        page = await context.new_page()

        # 解析 cookie 字符串并设置
        cookies_list = []
        for item in cookie_str.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)
                cookies_list.append({
                    'name': name,
                    'value': value,
                    'domain': '.glados.cloud',
                    'path': '/'
                })

        await context.add_cookies(cookies_list)

        try:
            # 访问签到页面
            logger.info('正在访问签到页面...')

            # 监听网络请求
            checkin_response = None

            async def handle_response(response):
                nonlocal checkin_response
                if '/api/user/checkin' in response.url:
                    checkin_response = await response.json()

            page.on('response', handle_response)

            await page.goto('https://glados.cloud/console/checkin', wait_until='domcontentloaded', timeout=60000)

            # 等待页面加载完成
            await asyncio.sleep(5)

            # 尝试查找签到按钮并点击
            try:
                # 尝试多种选择器
                selectors = [
                    'button:has-text("签到")',
                    'button:has-text("Check in")',
                    'button.btn-checkin',
                    'input[type="button"]',
                    'button',
                ]

                button_found = False
                for selector in selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            logger.info(f'找到按钮: {selector}')
                            await element.click()
                            button_found = True
                            # 等待响应
                            await asyncio.sleep(3)
                            break
                    except:
                        continue

                if not button_found:
                    # 尝试通过 JavaScript 触发签到
                    logger.info('尝试通过 JavaScript 触发签到...')
                    checkin_response = await page.evaluate('''async () => {
                        try {
                            const response = await fetch('https://glados.cloud/api/user/checkin', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json;charset=UTF-8'
                                },
                                body: JSON.stringify({token: 'glados.one'})
                            });
                            return await response.json();
                        } catch (e) {
                            return {error: e.toString()};
                        }
                    }''')

            except Exception as e:
                logger.info(f'点击按钮出错: {e}')

            return checkin_response

        finally:
            await browser.close()


async def get_account_status(cookie_str):
    """获取账号状态"""
    headers = {
        'cookie': cookie_str,
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get('https://glados.cloud/api/user/status', headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return data['data']
    except Exception as e:
        logger.info(f'获取状态出错: {e}')

    return None


# -------------------------------------------------------------------------------------------
# 主函数
# -------------------------------------------------------------------------------------------
async def main():
    # 设置日志
    setup_logger()

    # 加载配置
    config = load_config()

    # pushplus 秘钥
    sckey = config.get("pushplus_token", "")
    sendContent = ''

    # 获取 Cookie 列表
    cookies = config.get("cookies", [])
    if not cookies:
        logger.info('配置中未找到 Cookie')
        return

    logger.info(f'找到 {len(cookies)} 个账号，开始签到...\n')

    success_count = 0
    error_count = 0

    for idx, cookie_item in enumerate(cookies, 1):
        cookie = cookie_item.get("cookie", "")
        if not cookie:
            continue

        logger.info(f'[{idx}/{len(cookies)}] 正在签到...')

        try:
            # 使用 Playwright 签到
            result = await checkin_with_playwright(cookie)

            # 获取账号状态
            status = await get_account_status(cookie)

            if status:
                email = status.get('email', 'unknown')
                time_left = str(status.get('leftDays', '0')).split('.')[0]

                if result:
                    if 'message' in result:
                        mess = result['message']
                        result_str = f"{email}----结果--{mess}----剩余({time_left})天"
                        logger.info(result_str)
                        sendContent += result_str + "\n"
                        success_count += 1
                    else:
                        result_str = f"{email}----签到响应: {json.dumps(result, ensure_ascii=False)}"
                        logger.info(result_str)
                        sendContent += result_str + "\n"
                        success_count += 1
                else:
                    logger.info(f'{email} 签到无响应')
                    error_count += 1
            else:
                error_msg = f"获取账号状态失败，Cookie可能已失效"
                logger.info(error_msg)
                sendContent += error_msg + "\n"
                error_count += 1

        except Exception as e:
            logger.info(f'请求出错: {e}')
            sendContent += f"脚本运行出错: {e}\n"
            error_count += 1

        logger.info('')

    # PushPlus 推送
    if sckey and sendContent:
        try:
            push_url = 'http://www.pushplus.plus/send'
            data = {
                "token": sckey,
                "title": "GLaDOS签到结果通知",
                "content": sendContent,
                "template": "html"
            }
            requests.post(push_url, json=data)
            logger.info('已发送推送通知')
        except Exception as e:
            logger.info(f'推送失败: {e}')

    # 根据执行结果设置退出码
    if error_count > 0 or success_count == 0:
        logger.info(f'签到执行结束: 成功 {success_count}, 失败 {error_count}')
        sys.exit(1)
    else:
        logger.info(f'签到执行结束: 成功 {success_count}, 失败 {error_count}')
        sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())
