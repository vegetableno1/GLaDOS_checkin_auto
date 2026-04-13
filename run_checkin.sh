#!/bin/bash
# GLaDOS 自动签到运行脚本
# 失败时发送邮件通知

# 添加 PATH（cron 环境需要）
export PATH="$HOME/.local/bin:$PATH"

# 配置
PROJECT_DIR="/home/vone/2_Personal/GLaDOS_checkin_auto"
LOG_FILE="$PROJECT_DIR/logs/checkin_cron_$(date +%Y%m%d_%H%M%S).log"
EMAIL="529511657@qq.com"

# 加载 SMTP 配置
if [ -f "$PROJECT_DIR/.env.smtp" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env.smtp" | xargs)
fi

# 进入项目目录
cd "$PROJECT_DIR" || exit 1

# 运行签到脚本并捕获输出
echo "========================================" >> "$LOG_FILE"
echo "开始时间: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 运行脚本
if .venv/bin/python glados_playwright.py >> "$LOG_FILE" 2>&1; then
    EXIT_CODE=0
    STATUS="成功"
else
    EXIT_CODE=$?
    STATUS="失败 (退出码: $EXIT_CODE)"
fi

echo "========================================" >> "$LOG_FILE"
echo "结束时间: $(date)" >> "$LOG_FILE"
echo "状态: $STATUS" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 如果失败，发送邮件通知
if [ $EXIT_CODE -ne 0 ]; then
    echo "脚本执行失败，发送邮件通知..."
    python3 send_email.py "$EMAIL" "GLaDOS签到脚本执行失败" "脚本执行失败，退出码: $EXIT_CODE\n\n日志文件: $LOG_FILE\n\n请查看日志文件了解详情。"
fi

exit $EXIT_CODE
