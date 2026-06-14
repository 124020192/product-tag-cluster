#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商产品信息聚合与分析工具 v1.0

用法：
  1. 交互式模式：python product_monster.py
  2. 命令行模式：python product_monster.py --platform taobao --appkey KEY --secret SECRET --keyword 空调 --pages 5
  3. 配置文件模式：python product_monster.py --config config.json
  4. 模拟演示模式：python product_monster.py --mock

更多信息：参见 电商产品信息聚合工具_PRD_V1.0.md
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import (
    Config,
    interactive_input,
    load_from_args,
    load_from_config_file,
    validate_config,
    PLATFORM_NAMES,
)
from src.api_client import APIClient, MockAPIClient
from src.tag_engine import (
    process_tags,
    display_tags,
    select_tags_interactive,
    cluster_products,
    auto_select_tags,
)
from src.output_formatter import (
    display_clusters_console,
    save_to_json,
    save_to_csv,
    save_raw_items,
)


def print_banner():
    """打印程序横幅"""
    print()
    print("=" * 55)
    print("  电商产品信息聚合与分析工具 v1.0")
    print("  API 驱动 - 智能标签聚类 - 多平台支持")
    print("=" * 55)
    print()


def print_usage():
    """打印使用说明"""
    print("用法：")
    print("  python product_monster.py                    # 交互式模式")
    print("  python product_monster.py --mock              # 模拟演示模式")
    print("  python product_monster.py --config config.json # 配置文件模式")
    print("  python product_monster.py \\")
    print("      --platform taobao \\")
    print("      --appkey YOUR_APPKEY \\")
    print("      --secret YOUR_SECRET \\")
    print("      --keyword 空调 \\")
    print("      --pages 5 \\")
    print("      --pagesize 40")
    print()


def main():
    """主程序入口"""
    print_banner()

    args = sys.argv[1:]

    config = Config()

    if "--help" in args or "-h" in args:
        print_usage()
        return

    if "--mock" in args:
        print("[Mock] 模拟演示模式 - 使用模拟数据展示功能\n")
        config.platform = "taobao"
        config.appkey = "test_key"
        config.secret = "test_secret"
        config.keyword = "空调"
        config.pages = 1
        config.page_size = 40
        config.output_format = "json"
        config.output_dir = "./output"
    elif "--config" in args:
        idx = args.index("--config")
        if idx + 1 < len(args):
            config_path = args[idx + 1]
            print(f"[Config] 从配置文件加载: {config_path}")
            config = load_from_config_file(config_path)
        else:
            print("[Error] 请指定配置文件路径")
            return
    elif any(arg.startswith("--") for arg in args):
        config = load_from_args(args)
    else:
        config = interactive_input()

    valid, msg = validate_config(config)
    if not valid:
        print(f"\n[Error] 配置验证失败: {msg}")
        return

    print(f"\n[Info] 配置确认:")
    print(f"   平台: {PLATFORM_NAMES.get(config.platform, config.platform)}")
    print(f"   关键词: {config.keyword}")
    print(f"   搜索页数: {config.pages}")
    print(f"   每页数量: {config.page_size}")

    is_mock = "--mock" in args
    if is_mock:
        client = MockAPIClient(config)
    else:
        client = APIClient(config)

    items = client.search()

    if not items:
        print("\n[Error] 未搜索到相关商品数据")
        return

    print("\n[Tag] 正在提取商品标签...")
    tags = process_tags(items)

    if not tags:
        print("[Warning] 未提取到有效标签，将使用全部商品数据进行分析")

    if "--mock" in args or "--batch" in args:
        selected_tags = auto_select_tags(tags) if tags else []
        if selected_tags:
            print(f"[OK] 自动选择全部 {len(selected_tags)} 个标签")
    else:
        selected_tags = select_tags_interactive(tags)
        if selected_tags is None:
            return

    print("\n[Cluster] 正在进行聚类分析...")
    clusters = cluster_products(items, selected_tags)

    if not clusters:
        print("[Error] 无符合所选标签条件的产品，请扩大标签选择范围")
        return

    display_clusters_console(config, clusters, len(items), selected_tags)

    if config.output_format in ("json", "all"):
        try:
            save_to_json(config, clusters, selected_tags, len(items))
        except Exception as e:
            print(f"[Warning] JSON 文件保存失败: {e}，已在控制台展示结果")

    if config.output_format in ("csv", "all"):
        try:
            save_to_csv(config, clusters, selected_tags, len(items))
        except Exception as e:
            print(f"[Warning] CSV 文件保存失败: {e}，已在控制台展示结果")

    # 导出原始 API 数据（不经过聚类）
    if "--raw" in args or config.output_format == "raw":
        try:
            save_raw_items(items, config)
        except Exception as e:
            print(f"[Warning] 原始数据保存失败: {e}")

    print(f"\n[完成] 分析完成！共 {len(items)} 条商品，聚类为 {len(clusters)} 种类型")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[退出] 用户中断，程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Error] 程序异常: {e}")
        sys.exit(1)