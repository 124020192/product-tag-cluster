"""
配置模块 - 处理用户输入和配置文件
"""
import json
import os
import sys
from typing import Optional


# 默认配置
DEFAULT_CONFIG = {
    "platform": "taobao",
    "appkey": "",
    "secret": "",
    "keyword": "",
    "pages": 2,
    "page_size": 40,
    "output_format": "json",
    "output_dir": "./output",
}

# 万邦 API 基础地址
API_BASE_URL = {
    "taobao": "https://api-gw.onebound.cn/taobao/",
    "jd": "https://api-gw.onebound.cn/jd/",
}

# 平台名称映射
PLATFORM_NAMES = {
    "taobao": "淘宝",
    "jd": "京东",
}

# 平台搜索 API 类型
PLATFORM_SEARCH_API = {
    "taobao": "item_search",
    "jd": "item_search",
}


class Config:
    """配置类，管理用户输入和程序配置"""

    def __init__(self):
        self.platform: str = ""
        self.appkey: str = ""
        self.secret: str = ""
        self.keyword: str = ""
        self.pages: int = 2
        self.page_size: int = 40
        self.output_format: str = "json"
        self.output_dir: str = "./output"

    @staticmethod
    def get_platform_display_name(platform_code: str) -> str:
        """获取平台中文显示名称"""
        return PLATFORM_NAMES.get(platform_code, platform_code)

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "platform": self.platform,
            "appkey": self.appkey,
            "secret": self.secret,
            "keyword": self.keyword,
            "pages": self.pages,
            "page_size": self.page_size,
            "output_format": self.output_format,
            "output_dir": self.output_dir,
        }

    def get_api_base_url(self) -> str:
        """获取平台 API 基础 URL"""
        return API_BASE_URL.get(self.platform, API_BASE_URL["taobao"])

    def get_search_api_type(self) -> str:
        """获取搜索 API 类型"""
        return PLATFORM_SEARCH_API.get(self.platform, "item_search")


def load_from_args(args: list[str]) -> Config:
    """从命令行参数加载配置"""
    config = Config()
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--platform" and i + 1 < len(args):
            config.platform = args[i + 1].strip().lower()
            i += 2
        elif arg == "--appkey" and i + 1 < len(args):
            config.appkey = args[i + 1].strip()
            i += 2
        elif arg == "--secret" and i + 1 < len(args):
            config.secret = args[i + 1].strip()
            i += 2
        elif arg == "--keyword" and i + 1 < len(args):
            config.keyword = args[i + 1].strip()
            i += 2
        elif arg == "--pages" and i + 1 < len(args):
            try:
                config.pages = max(1, min(50, int(args[i + 1])))
            except ValueError:
                pass
            i += 2
        elif arg == "--pagesize" and i + 1 < len(args):
            try:
                config.page_size = max(1, min(40, int(args[i + 1])))
            except ValueError:
                pass
            i += 2
        elif arg == "--output" and i + 1 < len(args):
            config.output_format = args[i + 1].strip().lower()
            i += 2
        elif arg == "--output-dir" and i + 1 < len(args):
            config.output_dir = args[i + 1].strip()
            i += 2
        else:
            i += 1
    return config


def load_from_config_file(filepath: str) -> Config:
    """从配置文件加载配置"""
    config = Config()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        config.platform = data.get("platform", config.platform)
        config.appkey = data.get("appkey", config.appkey)
        config.secret = data.get("secret", config.secret)
        config.keyword = data.get("keyword", config.keyword)
        config.pages = max(1, min(50, int(data.get("pages", config.pages))))
        config.page_size = max(1, min(40, int(data.get("page_size", config.page_size))))
        config.output_format = data.get("output_format", config.output_format)
        config.output_dir = data.get("output_dir", config.output_dir)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"[Warning] 配置文件读取失败: {e}")
        print("将使用默认配置")
    return config


def interactive_input() -> Config:
    """交互式输入模式"""
    config = Config()
    
    print("\n" + "=" * 50)
    print("  电商产品信息聚合与分析工具 v1.0")
    print("=" * 50)
    print()

    # 平台选择
    while True:
        platform_input = input("请选择平台（淘宝 / 京东）：").strip()
        if platform_input.lower() in ("taobao", "淘宝", "tb"):
            config.platform = "taobao"
            break
        elif platform_input.lower() in ("jd", "京东"):
            config.platform = "jd"
            break
        elif platform_input == "":
            print("[Error] 平台不能为空，请重新输入")
            continue
        else:
            print("[Error] 平台仅支持「淘宝」或「京东」，请重新输入")
            continue

    # API Key
    while True:
        appkey = input(f"请输入【{PLATFORM_NAMES[config.platform]}】API Key（App Key）：").strip()
        if appkey:
            config.appkey = appkey
            break
        print("[Error] API Key 不能为空，请重新输入")

    # Secret
    while True:
        secret = input(f"请输入【{PLATFORM_NAMES[config.platform]}】API Secret：").strip()
        if secret:
            config.secret = secret
            break
        print("[Error] API Secret 不能为空，请重新输入")

    # 关键词
    while True:
        keyword = input("请输入要搜索的产品名称（如：空调）：").strip()
        if keyword:
            config.keyword = keyword
            break
        print("[Error] 产品名称不能为空，请重新输入")

    # 搜索页数（可选）
    while True:
        pages_input = input("请输入搜索页数（默认 2 页，API 每次调用消耗 1 次额度，最大 50）：").strip()
        if pages_input == "":
            config.pages = 2
            break
        try:
            pages = int(pages_input)
            if 1 <= pages <= 50:
                config.pages = pages
                break
            else:
                print("[Error] 页数必须在 1-50 之间")
        except ValueError:
            print("[Error] 请输入有效的数字")

    # 每页数量（可选）
    while True:
        page_size_input = input("请输入每页商品数（默认 40，最大 40）：").strip()
        if page_size_input == "":
            config.page_size = 40
            break
        try:
            ps = int(page_size_input)
            if 1 <= ps <= 40:
                config.page_size = ps
                break
            else:
                print("[Error] 每页数量必须在 1-40 之间")
        except ValueError:
            print("❌ 请输入有效的数字")

    return config


def validate_config(config: Config) -> tuple[bool, str]:
    """验证配置是否有效"""
    if config.platform not in ("taobao", "jd"):
        return False, f"平台「{config.platform}」不支持，仅支持淘宝和京东"
    if not config.appkey:
        return False, "API Key 不能为空"
    if not config.secret:
        return False, "API Secret 不能为空"
    if not config.keyword:
        return False, "产品名称不能为空"
    if config.pages < 1 or config.pages > 50:
        return False, f"搜索页数 {config.pages} 无效，必须在 1-50 之间"
    if config.page_size < 1 or config.page_size > 40:
        return False, f"每页数量 {config.page_size} 无效，必须在 1-40 之间"
    return True, "配置有效"