#!/usr/bin/env python3
"""
邮件发送脚本
使用 QQ 邮箱 SMTP 发送邮件通知
"""
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os

# SMTP 配置（需要配置 QQ 邮箱授权码）
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 587

# 从环境变量或配置文件读取发件人信息
SENDER_EMAIL = os.environ.get("SMTP_EMAIL", "")
SENDER_AUTH_CODE = os.environ.get("SMTP_AUTH_CODE", "")

def send_email(to_email, subject, content):
    """发送邮件"""
    if not SENDER_EMAIL or not SENDER_AUTH_CODE:
        print("错误: 未配置 SMTP_EMAIL 或 SMTP_AUTH_CODE 环境变量")
        print("请设置发件人邮箱和 QQ 邮箱授权码")
        return False

    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = formataddr(['GLaDOS签到脚本', SENDER_EMAIL])
        msg['To'] = to_email
        msg['Subject'] = subject

        # 添加邮件正文
        msg.attach(MIMEText(content, 'plain', 'utf-8'))

        # 连接 SMTP 服务器
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_AUTH_CODE)

        # 发送邮件
        server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
        server.quit()

        print(f"邮件已发送到: {to_email}")
        return True

    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python3 send_email.py <收件人> <主题> <内容>")
        sys.exit(1)

    to_email = sys.argv[1]
    subject = sys.argv[2]
    content = sys.argv[3] if len(sys.argv) > 3 else ""

    success = send_email(to_email, subject, content)
    sys.exit(0 if success else 1)
