# -*- coding: utf-8 -*-
"""
标签引擎模块 - 提取标签、展示标签、用户选择、聚类分析

核心设计：
- 标签主要来源：万邦 API 返回的 props_list（结构化属性），与品类无关
- 标题候选标签：从标题中提取所有可能的中文特征词，供用户手动确认
- 多层fallback机制确保任何关键词都能提取到标签
"""
import re
from collections import Counter
from typing import Optional


# 通用词黑名单（需要过滤的非特征词）
GENERIC_WORDS = {
    "正品", "包邮", "官方", "旗舰店", "专卖店", "专营店",
    "热卖", "爆款", "推荐", "特价", "促销", "优惠", "大促", "限时",
    "新品", "新款", "同款", "专柜", "专卖", "直营", "授权",
    "品牌", "品质", "放心", "保证", "保障", "售后", "服务",
    "全国", "联保", "免费", "赠送", "礼品", "送", "免邮",
    "家用", "商用", "出租房", "宿舍", "卧室", "客厅", "厨房", "办公", "餐厅",
    "官方正品", "以旧换新", "补贴", "政府补贴", "国补",
    "大1匹", "大1.5匹", "大2匹", "大3匹", "小1匹", "小1.5匹",
    "正1匹", "足1匹", "大一匹", "大二匹", "大三匹", "匹数",
    "普通商品", "商品标题", "这是一个", "更多", "精选",
    "参数", "型号", "规格", "配置",
    "颜色", "尺寸", "重量", "材质",
    "类型", "类别", "系列",
    # 搜索词本身不算特征（会在process_tags中动态过滤）
}


# 停用词（标题分词过滤用，这些词不具有特征性）
STOP_WORDS = {
    "这是", "一个", "不是", "就是", "可以", "没有", "我们", "他们", "它们",
    "什么", "怎么", "自己", "因为", "所以", "但是", "如果", "虽然",
    "商品", "产品", "价格", "促销", "大全", "批发", "定制", "厂家",
    "直销", "一件", "代发", "包邮", "满减", "折扣", "特卖", "今日",
    "推荐", "爆款", "精选", "套装", "组合", "系列", "新款", "同款",
    "官方", "正品", "品质", "保障", "放心", "无忧", "售后",
    "上门", "安装", "维修", "免费", "赠送", "礼品", "送装",
    "全国", "联保", "电话", "地址", "联系", "客服",
    "图片", "仅供参考", "具体", "实物", "为准",
    "说明", "描述", "详情", "点击", "进入", "购买",
    "立即", "下单", "抢购", "限量", "秒杀", "限时",
    "一年", "三年", "五年",
    "不用", "无需", "不需要",
}


# 同义词映射（合并同义词）
SYNONYM_MAP = {
    "变频空调": "变频",
    "定频空调": "定频",
    "壁挂式空调": "壁挂式",
    "壁挂": "壁挂式",
    "挂机": "壁挂式",
    "挂式": "壁挂式",
    "立柜式空调": "立柜式",
    "立柜": "立柜式",
    "柜机": "立柜式",
    "立式": "立柜式",
    "柜式": "立柜式",
    "冷暖型": "冷暖型",
    "冷暖": "冷暖型",
    "冷暖空调": "冷暖型",
    "单冷型": "单冷型",
    "单冷": "单冷型",
    "一级能效": "一级能效",
    "二级能效": "二级能效",
    "三级能效": "三级能效",
    "四级能效": "四级能效",
    "五级能效": "五级能效",
    "一级": "一级能效",
    "二级": "二级能效",
    "三级": "三级能效",
    "新一级": "新一级",
    "新三级": "新三级",
    "智能": "智能控制",
    "智能空调": "智能控制",
    "智能控制": "智能控制",
    "wifi": "智能控制",
    "自清洁": "自清洁",
    "自洁": "自清洁",
    "自动清洁": "自清洁",
    "1匹": "1匹",
    "1.5匹": "1.5匹",
    "2匹": "2匹",
    "3匹": "3匹",
    "4匹": "4匹",
    "5匹": "5匹",
    "大1.5匹": "1.5匹",
    "大1匹": "1匹",
    "大2匹": "2匹",
    "大3匹": "3匹",
    "对开门": "对开门",
    "十字对开": "十字对开门",
    "十字门": "十字对开门",
    "多门": "多门",
    "法式多门": "法式多门",
    "三门": "三门",
    "双门": "双门",
    "单门": "单门",
    "风冷无霜": "风冷",
    "滚筒洗衣机": "滚筒",
    "波轮洗衣机": "波轮",
    "洗烘一体机": "洗烘一体",
    "4K": "4K超高清",
    "4K超高清": "4K超高清",
    "8K": "8K超高清",
    "8K超高清": "8K超高清",
    "oled": "OLED",
    "qled": "QLED",
    "miniled": "MiniLED",
    "led": "LED",
    "lcd": "LCD",
    "智能手机": "智能手机",
    "5G手机": "5G",
    "双卡双待": "双卡双待",
    "双卡": "双卡双待",
    "鸿蒙": "鸿蒙系统",
    "harmonyos": "鸿蒙系统",
    "ios": "iOS系统",
    "iOS": "iOS系统",
    "android": "安卓",
    "公斤": "公斤",
    "kg": "公斤",
    "Kg": "公斤",
    "KG": "公斤",
    "斤": "斤",
    "寸": "寸",
    "英寸": "寸",
    "不锈钢": "不锈钢",
    "全铜": "全铜",
    "纯铜": "全铜",
}


# 标题关键词提取模式（覆盖品类无关的通用特征）
TITLE_PATTERNS = [
    r"(\d+\.?\d*\s*(升|L(?!E)|公斤|kg|Kg|KG|斤|寸|英寸|匹|毫升|ml|ML|瓦|W|w|伏|V|AH|ah|毫安|mAh|GB|gb|TB|tb|G|g))",
    r"(\d+\.?\d*(升|L(?!E)|公斤|kg|Kg|KG|斤|寸|英寸|匹|毫升|ml|ML|瓦|W|w|V|GB|gb|TB|tb))",
    r"(变频|定频|一级能效|二级能效|三级能效|新一级|新三级|超一级)",
    r"(智能|自清洁|节能|省电|静音|低噪|除菌|杀菌|消毒|净化|除湿|烘干|恒温|速冷|速热)",
    r"(蓝牙|WiFi|无线|语音|远程|APP|触控|触屏|全面屏|曲面屏|折叠屏|高清|超清)",
    r"(5G|4G|全网通|双卡|OLED|QLED|MiniLED|LED|LCD|4K|8K|HDR)",
    r"(滚筒|波轮|洗烘|全自动|对开|十字|风冷|直冷|多门|双门|三门|双开)",
    r"(壁挂式|壁挂|立柜式|立柜|中央空调|移动空调|新风|挂机|柜机|窗机|天花机)",
    r"(嵌入式|独立式|便携式|台式|立式|迷你|超薄|大容量|小型|家用)",
]


def extract_tags_from_title(title: str) -> list[str]:
    """从商品标题中用特征模式提取标签"""
    tags = []
    if not title:
        return tags
    for pattern in TITLE_PATTERNS:
        matches = re.finditer(pattern, title, re.IGNORECASE)
        for m in matches:
            tag = m.group(1) if m.lastindex and m.group(1) else m.group(0)
            tag = tag.strip()
            if tag and len(tag) >= 2:
                tags.append(tag)
    return tags


def extract_candidates_from_title(title: str) -> list[str]:
    """
    从标题提取所有候选标签（用于供用户手动选择）
    
    策略：提取标题中所有2-5字中文词，过滤停用词/通用词，
    再通过"重叠合并"去除子串关系（如"变频"和"变频空调"同时出现时保留更长的）
    """
    if not title:
        return []
    
    # 提取所有2-5字中文词
    words = re.findall(r"[\u4e00-\u9fff]{2,5}", title)
    
    # 过滤
    candidates = []
    for w in words:
        if w in GENERIC_WORDS or w in STOP_WORDS:
            continue
        # 过滤单个重复字（"哈哈哈""啊啊啊"）
        if len(set(w)) == 1:
            continue
        candidates.append(w)
    
    # 去重并移除子串关系：如果A是B的子串且它们同时存在，只保留B
    unique = list(dict.fromkeys(candidates))  # 去重保序
    result = []
    for w in unique:
        # 如果w是另一个候选词的子串，且另一个候选词也存在，跳过w
        is_sub = False
        for other in unique:
            if w != other and w in other:
                is_sub = True
                break
        if not is_sub:
            result.append(w)
    
    return result


def extract_tags_fallback(title: str) -> list[str]:
    """标题标签提取的fallback：中文字词提取"""
    tags = []
    if not title:
        return tags
    chinese_words = re.findall(r"[\u4e00-\u9fff]{2,4}", title)
    for word in chinese_words:
        if word in GENERIC_WORDS or word in STOP_WORDS:
            continue
        if len(set(word)) == 1 and len(word) >= 2:
            continue
        tags.append(word)
    return tags


def extract_tags_from_props(props_list: list) -> list[str]:
    """从商品属性列表中提取标签"""
    tags = []
    if not props_list:
        return tags
    for prop in props_list:
        if not prop or not isinstance(prop, str):
            continue
        prop = prop.strip()
        if not prop:
            continue
        if ":" in prop:
            key, value = prop.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                tags.append(value)
        else:
            tags.append(prop)
    return tags


def normalize_tag(tag: str) -> str:
    """标准化标签（同义词合并、去空格等）"""
    tag = tag.strip().lower()
    tag = re.sub(r"^(\d+\.?\d*)\s*匹$", lambda m: m.group(1) + "匹", tag)
    tag = re.sub(r"^(\d+\.?\d*)p$", lambda m: m.group(1) + "匹", tag)
    if tag in SYNONYM_MAP:
        return SYNONYM_MAP[tag]
    return tag


def is_generic_word(tag: str) -> bool:
    """判断是否为通用词"""
    return tag.lower() in {w.lower() for w in GENERIC_WORDS}


def process_tags(items: list[dict], keyword: str = "") -> dict[str, int]:
    """
    从商品列表中提取所有已验证的标签（已有标签），去重并统计频次
    
    返回：{标签名: 出现次数}
    """
    all_tags = []

    for item in items:
        item_tags = set()

        # 层1：API 的 props_list
        props = item.get("props_list", [])
        for t in extract_tags_from_props(props):
            normalized = normalize_tag(t)
            if normalized and not is_generic_word(normalized) and normalized != keyword:
                item_tags.add(normalized)

        title = item.get("title", "")

        # 层2：API 的 props_name
        props_name = item.get("props_name", "")
        if props_name and isinstance(props_name, str):
            for part in props_name.split(";"):
                part = part.strip()
                if ":" in part:
                    _, value = part.split(":", 1)
                    normalized = normalize_tag(value.strip())
                    if normalized and not is_generic_word(normalized) and normalized != keyword:
                        item_tags.add(normalized)

        # 层3：标题特征模式提取
        for t in extract_tags_from_title(title):
            normalized = normalize_tag(t)
            if normalized and not is_generic_word(normalized) and normalized != keyword:
                item_tags.add(normalized)

        # 层4：标题中文字词提取（作为补充）
        for t in extract_tags_fallback(title):
            normalized = normalize_tag(t)
            if normalized and not is_generic_word(normalized) and normalized != keyword:
                item_tags.add(normalized)

        all_tags.extend(item_tags)

    counter = Counter(all_tags)

    # 保留出现至少2次的标签
    filtered = {tag: count for tag, count in counter.items() if count >= 2}

    # 如果过滤后为空但有标签，保留全部
    if not filtered and counter:
        filtered = dict(counter)
    elif not filtered:
        return _extract_last_resort_tags(items, keyword)

    return dict(sorted(filtered.items(), key=lambda x: (-x[1], x[0])))


def extract_candidate_tags(items: list[dict], keyword: str = "") -> dict[str, int]:
    """
    从所有商品的标题中提取候选标签（供用户手动确认）
    
    返回已排序的候选标签字典 {标签名: 出现次数}，过滤掉搜索词
    """
    all_candidates = []

    for item in items:
        title = item.get("title", "")
        candidates = extract_candidates_from_title(title)
        all_candidates.extend(candidates)

    if not all_candidates:
        return {}

    counter = Counter(all_candidates)

    # 过滤：保留出现至少2次，且不是搜索词本身
    filtered = {
        tag: count for tag, count in counter.items()
        if count >= 2 and tag.lower() != keyword.lower()
    }

    # 如果过滤后为空，降级保留出现1次的
    if not filtered:
        filtered = {tag: count for tag, count in counter.items() if tag.lower() != keyword.lower()}

    # 按出现次数降序排序
    return dict(sorted(filtered.items(), key=lambda x: (-x[1], x[0])))


def _extract_last_resort_tags(items: list[dict], keyword: str = "") -> dict[str, int]:
    """终极fallback：从标题提取所有中文2字词"""
    all_words = []
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        words = re.findall(r"[\u4e00-\u9fff]{2}", title)
        for w in words:
            if w not in GENERIC_WORDS and w not in STOP_WORDS and w.lower() != keyword.lower():
                all_words.append(w)
    if all_words:
        counter = Counter(all_words)
        return dict(sorted(counter.items(), key=lambda x: (-x[1], x[0])))
    return {}


def get_item_tags(item: dict) -> set[str]:
    """获取单个商品的所有标准化标签"""
    tags = set()

    props = item.get("props_list", [])
    for t in extract_tags_from_props(props):
        normalized = normalize_tag(t)
        if normalized and not is_generic_word(normalized):
            tags.add(normalized)

    title = item.get("title", "")
    for t in extract_tags_from_title(title):
        normalized = normalize_tag(t)
        if normalized and not is_generic_word(normalized):
            tags.add(normalized)

    props_name = item.get("props_name", "")
    if props_name and isinstance(props_name, str):
        for part in props_name.split(";"):
            part = part.strip()
            if ":" in part:
                _, value = part.split(":", 1)
                normalized = normalize_tag(value.strip())
                if normalized and not is_generic_word(normalized):
                    tags.add(normalized)

    if not tags:
        for t in extract_tags_fallback(title):
            normalized = normalize_tag(t)
            if normalized and not is_generic_word(normalized):
                tags.add(normalized)

    return tags


def display_tags(tags: dict[str, int], total_products: int):
    """展示标签列表（带柱状图）"""
    if not tags:
        print("\n[Info] 未提取到有效标签")
        return
    max_count = max(tags.values()) if tags else 1
    bar_max_width = 30
    print()
    print("=" * 55)
    print("  市场标签统计（共 %d 个标签）" % len(tags))
    print("=" * 55)
    print()
    for i, (tag, count) in enumerate(tags.items(), 1):
        bar_width = int((count / max_count) * bar_max_width) if max_count > 0 else 0
        bar = "#" * bar_width
        print("  #%-2d %-14s 出现 %d 次  %s" % (i, tag, count, bar))
    print()
    print("=" * 55)
    print()


def select_tags_interactive(tags: dict[str, int]) -> list[str]:
    """交互式让用户选择关注的标签"""
    if not tags:
        print("[Info] 未提取到有效标签，将使用全部商品数据")
        return []
    tag_list = list(tags.keys())
    while True:
        display_tags(tags, sum(tags.values()))
        print("输入标签编号（用逗号分隔，如 1,3,5）来选择要关注的标签")
        print("或输入 all 选择全部，quit 退出，refresh 重新显示：")
        print()
        user_input = input("> ").strip()
        if user_input.lower() == "quit":
            print("[Info] 已退出程序")
            return None
        if user_input.lower() == "refresh":
            continue
        if user_input.lower() == "all":
            print("[OK] 已选择全部 %d 个标签" % len(tag_list))
            return tag_list
        selected_indices = set()
        parts = user_input.split(",")
        valid = True
        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                idx = int(part)
                if 1 <= idx <= len(tag_list):
                    selected_indices.add(idx - 1)
                else:
                    print("[Error] 编号 %d 无效，请输入 1-%d 之间的数字" % (idx, len(tag_list)))
                    valid = False
            except ValueError:
                print("[Error] %s 不是有效编号" % part)
                valid = False
        if not valid:
            continue
        if not selected_indices:
            print("[Error] 未选择任何标签，请重新输入")
            continue
        selected_tags = [tag_list[i] for i in sorted(selected_indices)]
        print("[OK] 已选择 %d 个标签: %s" % (len(selected_tags), ", ".join(selected_tags)))
        return selected_tags


def cluster_products(items: list[dict], selected_tags: list[str]) -> list[dict]:
    """根据选中的标签对商品进行聚类"""
    if selected_tags:
        selected_set = set(selected_tags)
    else:
        selected_set = None
    if not selected_set:
        all_tags = set()
        for item in items:
            all_tags.update(get_item_tags(item))
        selected_set = all_tags

    product_clusters: dict[frozenset, list[dict]] = {}
    for item in items:
        item_tags = get_item_tags(item)
        cluster_key = frozenset(item_tags & selected_set)
        if cluster_key not in product_clusters:
            product_clusters[cluster_key] = []
        product_clusters[cluster_key].append(item)

    clusters = []
    for cluster_key, cluster_items in product_clusters.items():
        if not cluster_key:
            continue
        prices = [
            float(item["price"])
            for item in cluster_items
            if item.get("price") and item["price"].replace(".", "").isdigit()
        ]
        total_sales = sum(
            int(item["sales"]) for item in cluster_items if item.get("sales")
        )
        clusters.append({
            "tags": sorted(cluster_key),
            "products": cluster_items,
            "product_count": len(cluster_items),
            "price_range": {
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0,
                "avg": round(sum(prices) / len(prices), 2) if prices else 0,
            },
            "total_sales": total_sales,
            "representative": cluster_items[0] if cluster_items else None,
            "is_low_sample": len(cluster_items) <= 2,
        })

    clusters.sort(key=lambda x: (-x["product_count"], x["tags"]))
    for i, cluster in enumerate(clusters, 1):
        cluster["type_id"] = i

    unmatched_items = [item for item in items if not (get_item_tags(item) & selected_set)]
    if unmatched_items:
        clusters.append({
            "type_id": len(clusters) + 1,
            "tags": ["其他"],
            "products": unmatched_items,
            "product_count": len(unmatched_items),
            "price_range": {"min": 0, "max": 0, "avg": 0},
            "total_sales": 0,
            "representative": unmatched_items[0],
            "is_low_sample": False,
        })
    return clusters


def auto_select_tags(tags: dict[str, int]) -> list[str]:
    """自动选择所有标签（非交互模式使用）"""
    return list(tags.keys())