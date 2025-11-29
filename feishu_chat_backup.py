#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书群聊消息备份工具
Feishu (Lark) Group Chat Backup Tool

功能：
1. 获取机器人所在的所有群组
2. 导出指定群组的历史消息
3. 下载消息中的图片和文件
4. 支持导出为 JSON 和 CSV 格式

使用前准备：
1. 在飞书开放平台 (https://open.feishu.cn) 创建企业自建应用
2. 获取 App ID 和 App Secret
3. 为应用添加以下权限：
   - im:chat:readonly（获取群组信息）
   - im:chat.group_info:readonly（读取群组信息）
   - im:message:readonly（获取消息）
   - im:message.group_at_msg:readonly（获取群组中所有消息）
   - im:resource（获取消息中的资源文件）
4. 发布应用版本
5. 将机器人添加到需要备份的群组中

Author: Claude Code Assistant
"""

import os
import sys
import json
import csv
import time
import logging
import argparse
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path

try:
    import requests
except ImportError:
    print("请先安装 requests 库: pip install requests")
    sys.exit(1)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('feishu_backup.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class FeishuChatBackup:
    """飞书群聊消息备份类"""

    # API 基础 URL
    BASE_URL = "https://open.feishu.cn/open-apis"

    # 消息类型映射
    MSG_TYPE_MAP = {
        "text": "文本",
        "image": "图片",
        "file": "文件",
        "audio": "音频",
        "video": "视频",
        "sticker": "表情",
        "share_chat": "群名片",
        "share_user": "个人名片",
        "post": "富文本",
        "interactive": "卡片消息",
        "merge_forward": "合并转发",
        "system": "系统消息",
    }

    def __init__(self, app_id: str, app_secret: str, output_dir: str = "backup"):
        """
        初始化

        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
            output_dir: 输出目录
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.access_token: Optional[str] = None
        self.token_expire_time: float = 0

        # 创建 session 以复用连接
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json; charset=utf-8"
        })

    def _get_tenant_access_token(self) -> str:
        """
        获取 tenant_access_token

        Returns:
            access_token 字符串
        """
        # 检查 token 是否仍然有效（提前 5 分钟刷新）
        if self.access_token and time.time() < self.token_expire_time - 300:
            return self.access_token

        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise Exception(f"获取 access_token 失败: {data.get('msg')}")

            self.access_token = data.get("tenant_access_token")
            # token 有效期通常是 2 小时
            expire = data.get("expire", 7200)
            self.token_expire_time = time.time() + expire

            logger.info("成功获取 tenant_access_token")
            return self.access_token

        except requests.RequestException as e:
            raise Exception(f"请求 access_token 接口失败: {e}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        发送 API 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            API 响应数据
        """
        token = self._get_tenant_access_token()
        url = f"{self.BASE_URL}{endpoint}"

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        response = self.session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()

        return response.json()

    def get_chat_list(self) -> List[Dict]:
        """
        获取机器人所在的群组列表

        Returns:
            群组列表
        """
        chats = []
        page_token = None

        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            try:
                data = self._make_request("GET", "/im/v1/chats", params=params)

                if data.get("code") != 0:
                    logger.error(f"获取群组列表失败: {data.get('msg')}")
                    break

                items = data.get("data", {}).get("items", [])
                chats.extend(items)

                # 检查是否有更多数据
                has_more = data.get("data", {}).get("has_more", False)
                page_token = data.get("data", {}).get("page_token")

                if not has_more or not page_token:
                    break

            except Exception as e:
                logger.error(f"获取群组列表异常: {e}")
                break

        logger.info(f"共获取到 {len(chats)} 个群组")
        return chats

    def get_chat_messages(
        self,
        chat_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page_size: int = 50
    ) -> List[Dict]:
        """
        获取群组历史消息

        Args:
            chat_id: 群组 ID
            start_time: 开始时间戳（秒），可选
            end_time: 结束时间戳（秒），可选
            page_size: 每页消息数量

        Returns:
            消息列表
        """
        messages = []
        page_token = None
        total_fetched = 0

        while True:
            params = {
                "container_id_type": "chat",
                "container_id": chat_id,
                "page_size": min(page_size, 50),  # API 限制最大 50
            }

            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            if page_token:
                params["page_token"] = page_token

            try:
                data = self._make_request("GET", "/im/v1/messages", params=params)

                if data.get("code") != 0:
                    error_msg = data.get("msg", "未知错误")
                    logger.error(f"获取消息失败: {error_msg}")
                    # 如果是权限问题，给出提示
                    if "permission" in error_msg.lower():
                        logger.error("请确保应用已获得 '获取群组中所有消息' 权限")
                    break

                items = data.get("data", {}).get("items", [])
                messages.extend(items)
                total_fetched += len(items)

                logger.info(f"已获取 {total_fetched} 条消息...")

                # 检查是否有更多数据
                has_more = data.get("data", {}).get("has_more", False)
                page_token = data.get("data", {}).get("page_token")

                if not has_more or not page_token:
                    break

                # 避免请求过快
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"获取消息异常: {e}")
                break

        logger.info(f"共获取到 {len(messages)} 条消息")
        return messages

    def download_resource(
        self,
        message_id: str,
        file_key: str,
        resource_type: str,
        save_dir: Path
    ) -> Optional[str]:
        """
        下载消息中的资源文件（图片、文件等）

        Args:
            message_id: 消息 ID
            file_key: 文件 key
            resource_type: 资源类型 (image/file)
            save_dir: 保存目录

        Returns:
            保存的文件路径，失败返回 None
        """
        save_dir.mkdir(parents=True, exist_ok=True)

        try:
            token = self._get_tenant_access_token()

            url = f"{self.BASE_URL}/im/v1/messages/{message_id}/resources/{file_key}"
            params = {"type": resource_type}
            headers = {"Authorization": f"Bearer {token}"}

            response = self.session.get(url, params=params, headers=headers, stream=True)
            response.raise_for_status()

            # 获取文件扩展名
            content_type = response.headers.get("Content-Type", "")
            ext = self._get_extension_from_content_type(content_type, resource_type)

            # 生成文件名
            file_hash = hashlib.md5(file_key.encode()).hexdigest()[:8]
            filename = f"{message_id}_{file_hash}{ext}"
            file_path = save_dir / filename

            # 保存文件
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"已下载: {filename}")
            return str(file_path)

        except Exception as e:
            logger.error(f"下载资源失败 ({file_key}): {e}")
            return None

    def _get_extension_from_content_type(self, content_type: str, resource_type: str) -> str:
        """根据 Content-Type 获取文件扩展名"""
        type_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        }

        for key, ext in type_map.items():
            if key in content_type:
                return ext

        # 默认扩展名
        if resource_type == "image":
            return ".jpg"
        return ".bin"

    def parse_message_content(self, message: Dict) -> Dict:
        """
        解析消息内容

        Args:
            message: 原始消息数据

        Returns:
            解析后的消息数据
        """
        msg_type = message.get("msg_type", "unknown")
        body = message.get("body", {})
        content_str = body.get("content", "{}")

        try:
            content = json.loads(content_str) if content_str else {}
        except json.JSONDecodeError:
            content = {"raw": content_str}

        parsed = {
            "message_id": message.get("message_id", ""),
            "msg_type": msg_type,
            "msg_type_name": self.MSG_TYPE_MAP.get(msg_type, msg_type),
            "create_time": message.get("create_time", ""),
            "update_time": message.get("update_time", ""),
            "sender_id": message.get("sender", {}).get("id", ""),
            "sender_type": message.get("sender", {}).get("sender_type", ""),
            "sender_tenant_key": message.get("sender", {}).get("tenant_key", ""),
        }

        # 转换时间戳为可读格式
        if parsed["create_time"]:
            try:
                ts = int(parsed["create_time"]) / 1000  # 毫秒转秒
                parsed["create_time_str"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                parsed["create_time_str"] = ""

        # 根据消息类型提取内容
        if msg_type == "text":
            parsed["text"] = content.get("text", "")
        elif msg_type == "image":
            parsed["image_key"] = content.get("image_key", "")
        elif msg_type == "file":
            parsed["file_key"] = content.get("file_key", "")
            parsed["file_name"] = content.get("file_name", "")
        elif msg_type == "post":
            # 富文本消息
            parsed["title"] = content.get("title", "")
            parsed["content"] = self._parse_post_content(content.get("content", []))
        elif msg_type == "interactive":
            # 卡片消息
            parsed["card"] = content
        else:
            parsed["content"] = content

        # 处理 @ 信息
        mentions = message.get("mentions", [])
        if mentions:
            parsed["mentions"] = [
                {
                    "key": m.get("key", ""),
                    "id": m.get("id", {}).get("open_id", ""),
                    "name": m.get("name", ""),
                }
                for m in mentions
            ]

        return parsed

    def _parse_post_content(self, content: List) -> str:
        """解析富文本内容为纯文本"""
        texts = []
        for paragraph in content:
            para_texts = []
            for element in paragraph:
                tag = element.get("tag", "")
                if tag == "text":
                    para_texts.append(element.get("text", ""))
                elif tag == "a":
                    para_texts.append(f"[{element.get('text', '')}]({element.get('href', '')})")
                elif tag == "at":
                    para_texts.append(f"@{element.get('user_name', '')}")
                elif tag == "img":
                    para_texts.append("[图片]")
            texts.append("".join(para_texts))
        return "\n".join(texts)

    def export_to_json(
        self,
        messages: List[Dict],
        chat_info: Dict,
        filename: str
    ) -> str:
        """
        导出消息为 JSON 格式

        Args:
            messages: 消息列表
            chat_info: 群组信息
            filename: 文件名

        Returns:
            保存的文件路径
        """
        export_data = {
            "export_time": datetime.now().isoformat(),
            "chat_info": {
                "chat_id": chat_info.get("chat_id", ""),
                "name": chat_info.get("name", ""),
                "description": chat_info.get("description", ""),
                "owner_id": chat_info.get("owner_id", ""),
            },
            "total_messages": len(messages),
            "messages": [self.parse_message_content(msg) for msg in messages]
        }

        file_path = self.output_dir / f"{filename}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"已导出 JSON: {file_path}")
        return str(file_path)

    def export_to_csv(
        self,
        messages: List[Dict],
        chat_info: Dict,
        filename: str
    ) -> str:
        """
        导出消息为 CSV 格式

        Args:
            messages: 消息列表
            chat_info: 群组信息
            filename: 文件名

        Returns:
            保存的文件路径
        """
        file_path = self.output_dir / f"{filename}.csv"

        # CSV 字段
        fieldnames = [
            "message_id", "create_time_str", "msg_type_name", "sender_id",
            "text", "file_name", "image_key", "file_key"
        ]

        parsed_messages = [self.parse_message_content(msg) for msg in messages]

        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(parsed_messages)

        logger.info(f"已导出 CSV: {file_path}")
        return str(file_path)

    def download_all_resources(
        self,
        messages: List[Dict],
        chat_name: str
    ) -> Dict[str, str]:
        """
        下载所有消息中的资源文件

        Args:
            messages: 消息列表
            chat_name: 群组名称

        Returns:
            文件 key 到本地路径的映射
        """
        resource_dir = self.output_dir / "resources" / self._sanitize_filename(chat_name)
        resource_map = {}

        for msg in messages:
            parsed = self.parse_message_content(msg)
            msg_id = parsed.get("message_id", "")

            # 下载图片
            if parsed.get("image_key"):
                local_path = self.download_resource(
                    msg_id, parsed["image_key"], "image", resource_dir / "images"
                )
                if local_path:
                    resource_map[parsed["image_key"]] = local_path

            # 下载文件
            if parsed.get("file_key"):
                local_path = self.download_resource(
                    msg_id, parsed["file_key"], "file", resource_dir / "files"
                )
                if local_path:
                    resource_map[parsed["file_key"]] = local_path

        return resource_map

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名，移除非法字符"""
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            name = name.replace(char, '_')
        return name.strip()[:100]  # 限制长度

    def backup_chat(
        self,
        chat_id: str,
        chat_name: str = "",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        download_resources: bool = True,
        export_format: str = "both"
    ) -> Dict:
        """
        备份单个群组的消息

        Args:
            chat_id: 群组 ID
            chat_name: 群组名称
            start_time: 开始时间戳
            end_time: 结束时间戳
            download_resources: 是否下载资源文件
            export_format: 导出格式 (json/csv/both)

        Returns:
            备份结果信息
        """
        logger.info(f"开始备份群组: {chat_name or chat_id}")

        chat_info = {
            "chat_id": chat_id,
            "name": chat_name or chat_id,
        }

        # 获取消息
        messages = self.get_chat_messages(chat_id, start_time, end_time)

        if not messages:
            logger.warning(f"群组 {chat_name or chat_id} 没有获取到消息")
            return {"status": "empty", "message_count": 0}

        # 生成文件名
        safe_name = self._sanitize_filename(chat_name or chat_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}"

        result = {
            "status": "success",
            "message_count": len(messages),
            "files": []
        }

        # 导出文件
        if export_format in ("json", "both"):
            json_path = self.export_to_json(messages, chat_info, filename)
            result["files"].append(json_path)

        if export_format in ("csv", "both"):
            csv_path = self.export_to_csv(messages, chat_info, filename)
            result["files"].append(csv_path)

        # 下载资源
        if download_resources:
            resource_map = self.download_all_resources(messages, chat_name or chat_id)
            result["resources_downloaded"] = len(resource_map)

        logger.info(f"群组 {chat_name or chat_id} 备份完成")
        return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="飞书群聊消息备份工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 列出所有群组
  python feishu_chat_backup.py --list-chats

  # 备份指定群组
  python feishu_chat_backup.py --chat-id oc_xxx

  # 备份所有群组
  python feishu_chat_backup.py --backup-all

  # 指定时间范围备份
  python feishu_chat_backup.py --chat-id oc_xxx --start-time 1609430400 --end-time 1609516800

  # 只导出 JSON 格式
  python feishu_chat_backup.py --chat-id oc_xxx --format json

  # 不下载资源文件
  python feishu_chat_backup.py --chat-id oc_xxx --no-download

环境变量:
  FEISHU_APP_ID      飞书应用 App ID
  FEISHU_APP_SECRET  飞书应用 App Secret
        """
    )

    # 认证参数
    parser.add_argument("--app-id", help="飞书应用 App ID（也可通过环境变量 FEISHU_APP_ID 设置）")
    parser.add_argument("--app-secret", help="飞书应用 App Secret（也可通过环境变量 FEISHU_APP_SECRET 设置）")

    # 操作参数
    parser.add_argument("--list-chats", action="store_true", help="列出所有群组")
    parser.add_argument("--chat-id", help="要备份的群组 ID")
    parser.add_argument("--backup-all", action="store_true", help="备份所有群组")

    # 可选参数
    parser.add_argument("--start-time", help="开始时间戳（秒）")
    parser.add_argument("--end-time", help="结束时间戳（秒）")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both", help="导出格式（默认: both）")
    parser.add_argument("--no-download", action="store_true", help="不下载资源文件")
    parser.add_argument("--output-dir", default="backup", help="输出目录（默认: backup）")

    args = parser.parse_args()

    # 获取认证信息
    app_id = args.app_id or os.environ.get("FEISHU_APP_ID")
    app_secret = args.app_secret or os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("错误: 请提供 App ID 和 App Secret")
        print("可以通过命令行参数 --app-id 和 --app-secret 提供")
        print("或者设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        sys.exit(1)

    # 创建备份实例
    backup = FeishuChatBackup(app_id, app_secret, args.output_dir)

    # 执行操作
    if args.list_chats:
        # 列出所有群组
        chats = backup.get_chat_list()
        print("\n群组列表:")
        print("-" * 80)
        for chat in chats:
            print(f"  ID: {chat.get('chat_id', '')}")
            print(f"  名称: {chat.get('name', '未命名')}")
            print(f"  描述: {chat.get('description', '无')}")
            print("-" * 80)
        print(f"\n共 {len(chats)} 个群组")

    elif args.chat_id:
        # 备份指定群组
        result = backup.backup_chat(
            chat_id=args.chat_id,
            start_time=args.start_time,
            end_time=args.end_time,
            download_resources=not args.no_download,
            export_format=args.format
        )
        print(f"\n备份结果:")
        print(f"  状态: {result['status']}")
        print(f"  消息数: {result['message_count']}")
        if result.get("files"):
            print(f"  导出文件: {', '.join(result['files'])}")
        if result.get("resources_downloaded"):
            print(f"  下载资源数: {result['resources_downloaded']}")

    elif args.backup_all:
        # 备份所有群组
        chats = backup.get_chat_list()
        print(f"\n开始备份 {len(chats)} 个群组...")

        for chat in chats:
            chat_id = chat.get("chat_id", "")
            chat_name = chat.get("name", "")

            result = backup.backup_chat(
                chat_id=chat_id,
                chat_name=chat_name,
                start_time=args.start_time,
                end_time=args.end_time,
                download_resources=not args.no_download,
                export_format=args.format
            )

            print(f"  {chat_name}: {result['message_count']} 条消息")

        print("\n所有群组备份完成!")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
