# 飞书群聊消息备份工具使用指南

## 功能概述

本工具可以帮助你备份飞书群聊的历史消息，支持以下功能：

- 获取机器人所在的所有群组列表
- 导出指定群组或所有群组的历史消息
- 下载消息中的图片和文件
- 支持导出为 JSON 和 CSV 两种格式
- 支持按时间范围筛选消息

## 准备工作

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn)
2. 登录后点击「创建应用」→「企业自建应用」
3. 填写应用名称（如"群聊备份"）和描述
4. 创建成功后，进入应用管理页面

### 2. 获取应用凭证

在应用管理页面的「凭证与基础信息」中获取：

- **App ID**: 格式如 `cli_xxxxxxxxxxxxxxxx`
- **App Secret**: 格式如 32 位字符串

### 3. 添加机器人能力

1. 在左侧菜单选择「应用能力」→「添加应用能力」
2. 添加「机器人」能力

### 4. 配置权限

在「开发配置」→「权限管理」中，搜索并添加以下权限：

| 权限名称 | 权限标识 | 说明 |
|---------|---------|------|
| 获取群组信息 | im:chat:readonly | 读取群组基本信息 |
| 读取群组信息 | im:chat.group_info:readonly | 读取群组详细信息 |
| 获取消息 | im:message:readonly | 获取消息内容 |
| 获取群组中所有消息 | im:message.group_at_msg:readonly | **重要**: 获取群聊历史消息 |
| 获取消息中的资源文件 | im:resource | 下载图片和文件 |

### 5. 发布应用版本

1. 在「版本管理与发布」中创建新版本
2. 填写版本说明并提交审核
3. 等待管理员审核通过

### 6. 将机器人添加到群组

1. 在飞书中打开需要备份的群聊
2. 点击群设置 → 群机器人 → 添加机器人
3. 搜索并添加你创建的应用机器人

## 安装依赖

```bash
pip install requests
```

## 配置认证信息

### 方式一：使用环境变量（推荐）

```bash
# 复制配置示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 App ID 和 App Secret
```

.env 文件内容：
```
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=your_app_secret_here
```

### 方式二：命令行参数

```bash
python feishu_chat_backup.py --app-id cli_xxx --app-secret xxx ...
```

## 使用方法

### 列出所有群组

```bash
python feishu_chat_backup.py --list-chats
```

输出示例：
```
群组列表:
--------------------------------------------------------------------------------
  ID: oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  名称: 项目讨论群
  描述: 项目相关讨论
--------------------------------------------------------------------------------
  ID: oc_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
  名称: 团队通知群
  描述: 无
--------------------------------------------------------------------------------

共 2 个群组
```

### 备份指定群组

```bash
# 备份单个群组
python feishu_chat_backup.py --chat-id oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 备份所有群组

```bash
python feishu_chat_backup.py --backup-all
```

### 指定时间范围

```bash
# 备份 2024年1月1日 到 2024年12月31日 的消息
python feishu_chat_backup.py --chat-id oc_xxx --start-time 1704067200 --end-time 1735689600
```

> 提示：可使用 [时间戳转换工具](https://tool.lu/timestamp/) 将日期转为时间戳

### 选择导出格式

```bash
# 只导出 JSON
python feishu_chat_backup.py --chat-id oc_xxx --format json

# 只导出 CSV
python feishu_chat_backup.py --chat-id oc_xxx --format csv

# 两种格式都导出（默认）
python feishu_chat_backup.py --chat-id oc_xxx --format both
```

### 不下载资源文件

```bash
# 只导出消息文本，不下载图片和文件
python feishu_chat_backup.py --chat-id oc_xxx --no-download
```

### 指定输出目录

```bash
python feishu_chat_backup.py --chat-id oc_xxx --output-dir /path/to/backup
```

## 使用启动脚本（简化操作）

```bash
# 添加执行权限
chmod +x run_backup.sh

# 列出群组
./run_backup.sh --list-chats

# 备份群组
./run_backup.sh --chat-id oc_xxx
```

## 输出文件说明

### 目录结构

```
backup/
├── 群组名称_20241201_120000.json    # JSON 格式导出
├── 群组名称_20241201_120000.csv     # CSV 格式导出
├── resources/
│   └── 群组名称/
│       ├── images/                   # 图片文件
│       │   └── msg_xxx_abc123.jpg
│       └── files/                    # 其他文件
│           └── msg_yyy_def456.pdf
└── feishu_backup.log                 # 运行日志
```

### JSON 格式示例

```json
{
  "export_time": "2024-12-01T12:00:00.000000",
  "chat_info": {
    "chat_id": "oc_xxx",
    "name": "项目讨论群",
    "description": "项目相关讨论"
  },
  "total_messages": 100,
  "messages": [
    {
      "message_id": "om_xxx",
      "msg_type": "text",
      "msg_type_name": "文本",
      "create_time": "1701417600000",
      "create_time_str": "2024-12-01 12:00:00",
      "sender_id": "ou_xxx",
      "text": "这是一条文本消息"
    },
    {
      "message_id": "om_yyy",
      "msg_type": "image",
      "msg_type_name": "图片",
      "create_time": "1701417660000",
      "create_time_str": "2024-12-01 12:01:00",
      "sender_id": "ou_yyy",
      "image_key": "img_xxx"
    }
  ]
}
```

### CSV 格式

CSV 文件包含以下列：
- message_id: 消息 ID
- create_time_str: 发送时间
- msg_type_name: 消息类型
- sender_id: 发送者 ID
- text: 文本内容
- file_name: 文件名
- image_key: 图片 key
- file_key: 文件 key

## 常见问题

### Q: 提示权限不足？

确保：
1. 已添加所有必需的权限
2. 应用版本已发布并审核通过
3. 机器人已添加到目标群组

### Q: 获取不到历史消息？

确保已添加 `im:message.group_at_msg:readonly` 权限，这是获取群组历史消息的关键权限。

### Q: 如何获取更早的历史消息？

由于飞书 API 的限制，只能获取机器人加入群组后的消息。如需备份更早的消息，需要确保机器人尽早加入群组。

### Q: 导出的消息包含哪些类型？

支持的消息类型：
- 文本消息
- 图片消息
- 文件消息
- 富文本消息（Post）
- 表情消息
- 卡片消息
- 群名片/个人名片
- 系统消息

### Q: API 请求限制？

飞书 API 有请求频率限制，脚本已内置适当的延迟。如遇到限流，请稍后重试。

## 安全提示

- 请妥善保管 App Secret，不要将其提交到代码仓库
- 建议使用 .env 文件配置敏感信息，并将 .env 添加到 .gitignore
- 备份文件可能包含敏感信息，请注意存储安全

## 参考资源

- [飞书开放平台官方文档](https://open.feishu.cn/document/home/index)
- [获取会话历史消息 API](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/list)
- [GitHub: dicarne/feishu-backup](https://github.com/dicarne/feishu-backup)
- [GitHub: cyclone-robotics/feishu-python-sdk](https://github.com/cyclone-robotics/feishu-python-sdk)
