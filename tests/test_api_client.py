"""
API 客户端模块单元测试
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import Config
from src.api_client import APIClient, MockAPIClient


class TestAPIClient(unittest.TestCase):
    """API 客户端测试"""

    def setUp(self):
        self.config = Config()
        self.config.platform = "taobao"
        self.config.appkey = "test_key"
        self.config.secret = "test_secret"
        self.config.keyword = "空调"
        self.config.pages = 1
        self.config.page_size = 10
        self.client = APIClient(self.config)

    def test_build_request_url(self):
        """测试构建请求 URL"""
        url = self.client._build_request_url(1, 10)
        self.assertIn("key=test_key", url)
        self.assertIn("q=%E7%A9%BA%E8%B0%83", url)  # URL-encoded 空调
        self.assertIn("page=1", url)
        self.assertIn("page_size=10", url)
        self.assertIn("taobao", url)
        self.assertIn("item_search", url)

    def test_normalize_item(self):
        """测试商品数据标准化"""
        raw_item = {
            "num_iid": "12345",
            "title": "测试商品",
            "price": "2999",
            "sales": 100,
            "nick": "测试店铺",
            "detail_url": "http://example.com",
            "pic_url": "http://example.com/pic.jpg",
            "props_name": "类型:壁挂式;匹数:1.5匹",
            "props_list": ["类型:壁挂式", "匹数:1.5匹"],
            "category_name": "家用电器",
            "seller_info": {"shop_name": "测试店铺"},
        }
        normalized = self.client._normalize_item(raw_item)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["num_iid"], "12345")
        self.assertEqual(normalized["title"], "测试商品")
        self.assertEqual(normalized["price"], "2999")
        self.assertEqual(normalized["platform"], "taobao")
        self.assertEqual(normalized["platform_name"], "淘宝")

    def test_normalize_item_props_string(self):
        """测试 props_list 为字符串时的处理"""
        raw_item = {
            "num_iid": "12345",
            "title": "测试商品",
            "price": "2999",
            "sales": 0,
            "nick": "测试店铺",
            "detail_url": "",
            "pic_url": "",
            "props_name": "",
            "props_list": "类型:壁挂式;匹数:1.5匹",
        }
        normalized = self.client._normalize_item(raw_item)
        self.assertIsNotNone(normalized)
        self.assertTrue(len(normalized["props_list"]) > 0)


class TestMockAPIClient(unittest.TestCase):
    """模拟 API 客户端测试"""

    def setUp(self):
        self.config = Config()
        self.config.platform = "taobao"
        self.config.appkey = "test_key"
        self.config.secret = "test_secret"
        self.config.keyword = "空调"
        self.config.pages = 1
        self.config.page_size = 10
        self.client = MockAPIClient(self.config)

    def test_generate_mock_items(self):
        """测试生成模拟数据"""
        items = self.client._generate_mock_items(1)
        self.assertEqual(len(items), 10)
        item = items[0]
        self.assertIn("num_iid", item)
        self.assertIn("title", item)
        self.assertIn("price", item)
        self.assertIn("shop_name", item)
        self.assertIn("props_list", item)

    def test_search(self):
        """测试模拟搜索"""
        items = self.client.search()
        self.assertEqual(len(items), 10)  # 1 page * 10 items
        for item in items:
            self.assertIn("空调", item["title"])

    def test_search_multiple_pages(self):
        """测试多页搜索"""
        self.config.pages = 3
        client = MockAPIClient(self.config)
        items = client.search()
        self.assertEqual(len(items), 30)  # 3 pages * 10 items


if __name__ == "__main__":
    unittest.main()