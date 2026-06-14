# -*- coding: utf-8 -*-
"""
输出格式化模块 - 控制台展示和文件输出
"""
import json
import os
import csv
from datetime import datetime
from typing import Optional
from .config import Config


def _format_price(price: float) -> str:
    """格式化价格显示"""
    return "%.0f 元" % price if price >= 1 else "%.2f 元" % price


def display_clusters_console(
    config: Config,
    clusters: list[dict],
    total_products: int,
    selected_tags: list[str],
):
    """在控制台展示聚类结果"""
    keyword = config.keyword
    platform_name = config.get_platform_display_name(config.platform)
    total_types = len(clusters)

    print()
    print("=" * 60)
    print("  %s -- 产品类型分析结果" % keyword)
    print("  平台：%s" % platform_name)
    print("=" * 60)
    print("  共 %d 条商品，聚类为 %d 种产品类型" % (total_products, total_types))
    if selected_tags:
        print("  筛选标签：%s" % ("、".join(selected_tags)))
    print()

    for cluster in clusters:
        tag_str = " | ".join(cluster["tags"])
        price_range = cluster["price_range"]
        rep = cluster.get("representative", {})
        rep_title = rep.get("title", "无") if rep else "无"
        rep_shop = rep.get("shop_name", "") if rep else ""
        rep_price = rep.get("price", "0") if rep else "0"

        low_sample_mark = " [低样本]" if cluster.get("is_low_sample") else ""

        print("-" * 60)
        print("  类型 #%d（%d 个商品）%s" % (cluster["type_id"], cluster["product_count"], low_sample_mark))
        print("    特征：%s" % tag_str)
        print("    价格区间：%s - %s" % (_format_price(price_range["min"]), _format_price(price_range["max"])))
        print("    平均价格：%s" % _format_price(price_range["avg"]))
        print("    总销量：%d" % cluster["total_sales"])
        print("    代表商品：%s" % rep_title)
        if rep_shop:
            print("    店铺：%s" % rep_shop)

    print("-" * 60)
    print()

    if total_types > 30:
        print("提示：检测到 %d 种产品类型，建议缩小标签选择范围以获得更精准的结果" % total_types)

    if total_types == 1:
        print("提示：所有商品特征高度一致，仅识别到 1 种产品类型")


def save_to_json(
    config: Config,
    clusters: list[dict],
    selected_tags: list[str],
    total_products: int,
) -> str:
    """保存聚类结果为 JSON 文件"""
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "%s_%s.json" % (config.keyword, timestamp)
    filepath = os.path.join(output_dir, filename)

    output = {
        "meta": {
            "platform": config.platform,
            "platform_name": config.get_platform_display_name(config.platform),
            "keyword": config.keyword,
            "total_products": total_products,
            "total_types": len(clusters),
            "selected_tags": selected_tags or [],
            "search_pages": config.pages,
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "product_types": [],
    }

    for cluster in clusters:
        rep = cluster.get("representative", {})
        type_info = {
            "type_id": cluster["type_id"],
            "product_count": cluster["product_count"],
            "tags": cluster["tags"],
            "price_range": {
                "min": cluster["price_range"]["min"],
                "max": cluster["price_range"]["max"],
                "avg": cluster["price_range"]["avg"],
            },
            "total_sales": cluster["total_sales"],
            "is_low_sample": cluster.get("is_low_sample", False),
            "representative_product": {
                "title": rep.get("title", "") if rep else "",
                "shop": rep.get("shop_name", "") if rep else "",
                "price": rep.get("price", "0") if rep else "0",
                "url": rep.get("detail_url", "") if rep else "",
                "sales": rep.get("sales", 0) if rep else 0,
            } if rep else None,
        }

        if cluster["product_count"] <= 5:
            type_info["products"] = []
            for item in cluster["products"]:
                type_info["products"].append({
                    "title": item.get("title", ""),
                    "price": item.get("price", "0"),
                    "shop": item.get("shop_name", ""),
                    "url": item.get("detail_url", ""),
                    "sales": item.get("sales", 0),
                })

        output["product_types"].append(type_info)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n结果已保存至 %s" % filepath)
    return filepath


def save_to_csv(
    config: Config,
    clusters: list[dict],
    selected_tags: list[str],
    total_products: int,
) -> str:
    """保存聚类结果为 CSV 文件"""
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "%s_%s.csv" % (config.keyword, timestamp)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "类型编号", "商品数量", "特征标签", "最低价", "最高价",
            "均价", "总销量", "代表商品", "店铺", "低样本标记"
        ])

        for cluster in clusters:
            rep = cluster.get("representative", {})
            writer.writerow([
                cluster["type_id"],
                cluster["product_count"],
                " | ".join(cluster["tags"]),
                _format_price(cluster["price_range"]["min"]),
                _format_price(cluster["price_range"]["max"]),
                _format_price(cluster["price_range"]["avg"]),
                cluster["total_sales"],
                rep.get("title", "") if rep else "",
                rep.get("shop_name", "") if rep else "",
                "是" if cluster.get("is_low_sample") else "否",
            ])

    print("\n结果已保存至 %s" % filepath)
    return filepath


def save_raw_items(items: list[dict], config: Config) -> str:
    """
    保存 API 返回的原始商品数据（直接导出，不经过聚类）
    这是用户要求的"导出api调取的直接结果"
    """
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "%s_%s_raw.json" % (config.keyword, timestamp)
    filepath = os.path.join(output_dir, filename)

    # 精简输出，只保留关键字段，去掉不必要的内部数据结构
    output_items = []
    for item in items:
        output_items.append({
            "num_iid": item.get("num_iid", ""),
            "title": item.get("title", ""),
            "price": item.get("price", "0"),
            "sales": item.get("sales", 0),
            "shop_name": item.get("shop_name", ""),
            "detail_url": item.get("detail_url", ""),
            "pic_url": item.get("pic_url", ""),
            "props_name": item.get("props_name", ""),
            "props_list": item.get("props_list", []),
            "category_name": item.get("category_name", ""),
            "cat_name": item.get("cat_name", ""),
        })

    output = {
        "meta": {
            "platform": config.platform,
            "platform_name": config.get_platform_display_name(config.platform),
            "keyword": config.keyword,
            "total_results": len(items),
            "search_pages": config.pages,
            "page_size": config.page_size,
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "items": output_items,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n原始数据已保存至 %s（共 %d 条商品）" % (filepath, len(items)))
    return filepath