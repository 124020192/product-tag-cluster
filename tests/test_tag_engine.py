# -*- coding: utf-8 -*-
"""标签引擎模块单元测试"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tag_engine import (
    extract_tags_from_title,
    extract_tags_from_props,
    normalize_tag,
    is_generic_word,
    process_tags,
    get_item_tags,
    cluster_products,
)


class TestExtractTagsFromTitle(unittest.TestCase):
    """标题标签提取测试"""

    def test_extract_type_tag(self):
        tags = extract_tags_from_title("格力云佳 壁挂式 变频 冷暖 空调")
        self.assertIn("壁挂式", tags)

    def test_extract_inverter_tag(self):
        tags = extract_tags_from_title("美的变频空调 1.5匹 一级能效")
        self.assertIn("变频", tags)

    def test_extract_hp_tag(self):
        tags = extract_tags_from_title("格力空调 1.5匹 变频")
        hp_tags = [t for t in tags if "匹" in t]
        self.assertTrue(len(hp_tags) > 0)

    def test_extract_energy_tag(self):
        tags = extract_tags_from_title("奥克斯空调 一级能效 变频")
        self.assertIn("一级能效", tags)

    def test_empty_title(self):
        tags = extract_tags_from_title("")
        self.assertEqual(tags, [])

    def test_no_tags(self):
        tags = extract_tags_from_title("这是一个普通商品标题")
        self.assertEqual(tags, [])


class TestExtractTagsFromProps(unittest.TestCase):
    """属性标签提取测试"""

    def test_extract_prop_values(self):
        props = ["匹数:1.5匹", "类型:壁挂式", "能效:一级"]
        tags = extract_tags_from_props(props)
        self.assertIn("1.5匹", tags)
        self.assertIn("壁挂式", tags)
        self.assertIn("一级", tags)

    def test_empty_props(self):
        tags = extract_tags_from_props([])
        self.assertEqual(tags, [])

    def test_prop_no_colon(self):
        props = ["变频", "冷暖型"]
        tags = extract_tags_from_props(props)
        self.assertIn("变频", tags)
        self.assertIn("冷暖型", tags)


class TestNormalizeTag(unittest.TestCase):
    """标签标准化测试"""

    def test_normalize_synonym(self):
        self.assertEqual(normalize_tag("壁挂"), "壁挂式")
        self.assertEqual(normalize_tag("挂机"), "壁挂式")
        self.assertEqual(normalize_tag("柜机"), "立柜式")
        self.assertEqual(normalize_tag("变频空调"), "变频")

    def test_normalize_hp(self):
        self.assertEqual(normalize_tag("1.5匹"), "1.5匹")
        self.assertEqual(normalize_tag("2匹"), "2匹")

    def test_normalize_case(self):
        self.assertEqual(normalize_tag("WiFi"), "智能控制")


class TestIsGenericWord(unittest.TestCase):
    """通用词判断测试"""

    def test_generic_words(self):
        self.assertTrue(is_generic_word("正品"))
        self.assertTrue(is_generic_word("包邮"))
        self.assertTrue(is_generic_word("官方"))

    def test_not_generic(self):
        self.assertFalse(is_generic_word("壁挂式"))
        self.assertFalse(is_generic_word("变频"))
        self.assertFalse(is_generic_word("1.5匹"))


class TestGetItemTags(unittest.TestCase):
    """获取商品标签测试"""

    def test_get_tags_from_props(self):
        item = {
            "title": "格力空调",
            "props_list": ["类型:壁挂式", "匹数:1.5匹"],
            "props_name": "",
        }
        tags = get_item_tags(item)
        self.assertIn("壁挂式", tags)
        self.assertIn("1.5匹", tags)

    def test_get_tags_from_title(self):
        item = {
            "title": "格力 变频空调 1.5匹 一级能效",
            "props_list": [],
            "props_name": "",
        }
        tags = get_item_tags(item)
        self.assertIn("变频", tags)

    def test_no_tags(self):
        item = {
            "title": "普通商品",
            "props_list": [],
            "props_name": "",
        }
        tags = get_item_tags(item)
        self.assertEqual(tags, set())


class TestProcessTags(unittest.TestCase):
    """标签处理测试（注意：出现次数<2的标签会被过滤）"""

    def setUp(self):
        self.items = [
            {
                "title": "格力空调 壁挂式 变频 1.5匹",
                "props_list": ["类型:壁挂式", "匹数:1.5匹"],
                "props_name": "类型:壁挂式;匹数:1.5匹",
            },
            {
                "title": "美的空调 壁挂式 变频 1.5匹 一级能效",
                "props_list": ["类型:壁挂式", "匹数:1.5匹", "能效:一级能效"],
                "props_name": "类型:壁挂式;匹数:1.5匹;能效:一级能效",
            },
            {
                "title": "海尔空调 立柜式 变频 3匹",
                "props_list": ["类型:立柜式", "匹数:3匹"],
                "props_name": "类型:立柜式;匹数:3匹",
            },
        ]

    def test_process_tags(self):
        tags = process_tags(self.items)
        self.assertIn("壁挂式", tags)
        self.assertIn("变频", tags)
        self.assertIn("1.5匹", tags)

    def test_process_tags_frequency(self):
        tags = process_tags(self.items)
        self.assertEqual(tags.get("壁挂式"), 2)
        self.assertEqual(tags.get("变频"), 3)

    def test_empty_items(self):
        tags = process_tags([])
        self.assertEqual(tags, {})


class TestClusterProducts(unittest.TestCase):
    """聚类测试"""

    def setUp(self):
        self.items = [
            {
                "title": "格力 壁挂式 变频 1.5匹",
                "price": "2999",
                "sales": 1000,
                "props_list": ["壁挂式", "变频", "1.5匹"],
                "props_name": "",
                "shop_name": "格力旗舰店",
                "detail_url": "http://example.com/1",
            },
            {
                "title": "美的 壁挂式 变频 1.5匹",
                "price": "2599",
                "sales": 2000,
                "props_list": ["壁挂式", "变频", "1.5匹"],
                "props_name": "",
                "shop_name": "美的旗舰店",
                "detail_url": "http://example.com/2",
            },
            {
                "title": "海尔 立柜式 变频 3匹",
                "price": "5999",
                "sales": 500,
                "props_list": ["立柜式", "变频", "3匹"],
                "props_name": "",
                "shop_name": "海尔旗舰店",
                "detail_url": "http://example.com/3",
            },
        ]

    def test_cluster_with_selected_tags(self):
        selected_tags = ["壁挂式", "变频", "1.5匹", "立柜式", "3匹"]
        clusters = cluster_products(self.items, selected_tags)
        self.assertTrue(len(clusters) >= 2)

    def test_cluster_without_tags(self):
        clusters = cluster_products(self.items, [])
        self.assertTrue(len(clusters) >= 2)

    def test_cluster_price_range(self):
        selected_tags = ["壁挂式", "变频", "1.5匹"]
        clusters = cluster_products(self.items[:2], selected_tags)
        if clusters:
            self.assertTrue(clusters[0]["price_range"]["min"] > 0)

    def test_empty_items(self):
        clusters = cluster_products([], ["壁挂式"])
        self.assertEqual(clusters, [])


if __name__ == "__main__":
    unittest.main()