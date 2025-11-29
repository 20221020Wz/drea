#!/bin/bash
# 飞书群聊消息备份启动脚本

# 加载环境变量（如果存在 .env 文件）
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 检查依赖
if ! python3 -c "import requests" 2>/dev/null; then
    echo "正在安装依赖..."
    pip3 install requests
fi

# 运行备份脚本
python3 feishu_chat_backup.py "$@"
