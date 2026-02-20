import requests,json,os
# -------------------------------------------------------------------------------------------
# github workflows
# -------------------------------------------------------------------------------------------
if __name__ == '__main__':
    # pushplus 秘钥
    sckey = os.environ.get("PUSHPLUS_TOKEN", "")
    sendContent = ''
    
    # 获取并分割 Cookie
    cookie_str = os.environ.get("GLADOS_COOKIE", "")
    if not cookie_str:
        print('未获取到 COOKIE 变量')
        exit(0)
    cookies = cookie_str.split("&")

    # 关键配置更新
    url = "https://glados.cloud/api/user/checkin"
    url2 = "https://glados.cloud/api/user/status"
    referer = 'https://glados.cloud/console/checkin'
    origin = "https://glados.cloud"
    # 使用较新的 User-Agent
    useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    payload = {'token': 'glados.one'}

    for cookie in cookies:
        headers = {
            'cookie': cookie,
            'referer': referer,
            'origin': origin,
            'user-agent': useragent,
            'content-type': 'application/json;charset=UTF-8'
        }
        
        try:
            # 签到请求
            checkin = requests.post(url, headers=headers, data=json.dumps(payload))
            # 状态查询
            state = requests.get(url2, headers=headers)
            
            if 'data' in state.json():
                time_left = str(state.json()['data']['leftDays']).split('.')[0]
                email = state.json()['data']['email']
                
                if 'message' in checkin.json():
                    mess = checkin.json()['message']
                    result = f"{email}----结果--{mess}----剩余({time_left})天"
                    print(result)
                    sendContent += result + "\n"
                else:
                    print(f"{email} 签到响应异常")
            else:
                # 可能是 Cookie 失效或被网站防火墙拦截 (Cloudflare)
                error_msg = f"Cookie失效或触发防火墙，请检查: {cookie[:20]}..."
                print(error_msg)
                sendContent += error_msg + "\n"
                
        except Exception as e:
            print(f"请求出错: {e}")
            sendContent += f"脚本运行出错，请检查日志\n"

    # PushPlus 推送
    if sckey:
        push_url = 'http://www.pushplus.plus/send'
        data = {
            "token": sckey,
            "title": "GLaDOS签到结果通知",
            "content": sendContent,
            "template": "html"
        }
        requests.post(push_url, data=json.dumps(data))


