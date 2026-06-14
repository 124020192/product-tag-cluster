"""
配置模块单元测试
"""
import sys
import os
import json
import tempfile
import unittest

# 添加项目根目录到导入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    Config,
    interactive_input,
    load_from_args,
    load_from_config_file,
    validate_config,
)


class TestConfig(unittest.TestCase):
    """配置类测试"""

    def test_config_defaults(self):
        """测试默认值"""
        config = Config()
        self.assertEqual(config.platform, "")
        self.assertEqual(config.appkey, "")
        self.assertEqual(config.secret, "")
        self.assertEqual(config.keyword, "")
        self.assertEqual(config.pages, 2)
        self.assertEqual(config.page_size, 40)
        self.assertEqual(config.output_format, "json")
        self.assertEqual(config.output_dir, "./output")

    def test_config_to_dict(self):
        """测试转字典"""
        config = Config()
        config.platform = "taobao"
        config.keyword = "空调"
        d = config.to_dict()
        self.assertEqual(d["platform"], "taobao")
        self.assertEqual(d["keyword"], "空调")

    def test_get_platform_display_name(self):
        """测试平台中文名"""
        self.assertEqual(Config.get_platform_display_name("taobao"), "淘宝")
        self.assertEqual(Config.get_platform_display_name("jd"), "京东")
        self.assertEqual(Config.get_platform_display_name("unknown"), "unknown")

    def test_get_api_base_url(self):
        """测试 API 基础 URL"""
        config = Config()
        config.platform = "taobao"
        self.assertEqual(config.get_api_base_url(), "https://api-gw.onebound.cn/taobao/")
        config.platform = "jd"
        self.assertEqual(config.get_api_base_url(), "https://api-gw.onebound.cn/jd/")

    def test_get_search_api_type(self):
        """测试搜索 API 类型"""
        config = Config()
        config.platform = "taobao"
        self.assertEqual(config.get_search_api_type(), "item_search")
        config.platform = "jd"
        self.assertEqual(config.get_search_api_type(), "item_search")


class TestLoadFromArgs(unittest.TestCase):
    """命令行参数加载测试"""

    def test_load_minimal_args(self):
        """测试最小参数"""
        args = ["--platform", "taobao", "--appkey", "abc", "--secret", "123", "--keyword", "空调"]
        config = load_from_args(args)
        self.assertEqual(config.platform, "taobao")
        self.assertEqual(config.appkey, "abc")
        self.assertEqual(config.secret, "123")
        self.assertEqual(config.keyword, "空调")
        self.assertEqual(config.pages, 2)  # 默认
        self.assertEqual(config.page_size, 40)  # 默认

    def test_load_all_args(self):
        """测试全部参数"""
        args = [
            "--platform", "jd",
            "--appkey", "test_key",
            "--secret", "test_secret",
            "--keyword", "手机",
            "--pages", "3",
            "--pagesize", "20",
            "--output", "csv",
            "--output-dir", "./my_output",
        ]
        config = load_from_args(args)
        self.assertEqual(config.platform, "jd")
        self.assertEqual(config.appkey, "test_key")
        self.assertEqual(config.keyword, "手机")
        self.assertEqual(config.pages, 3)
        self.assertEqual(config.page_size, 20)
        self.assertEqual(config.output_format, "csv")
        self.assertEqual(config.output_dir, "./my_output")

    def test_load_args_clamp_values(self):
        """测试参数值限制"""
        args = ["--platform", "taobao", "--appkey", "k", "--secret", "s", "--keyword", "k",
                "--pages", "100", "--pagesize", "100"]
        config = load_from_args(args)
        self.assertEqual(config.pages, 50)  # 应被限制在 50
        self.assertEqual(config.page_size, 40)  # 应被限制在 40


class TestLoadFromConfigFile(unittest.TestCase):
    """配置文件加载测试"""

    def test_load_valid_config(self):
        """测试有效配置文件"""
        config_data = {
            "platform": "taobao",
            "appkey": "config_key",
            "secret": "config_secret",
            "keyword": "冰箱",
            "pages": 10,
            "page_size": 30,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            config = load_from_config_file(config_path)
            self.assertEqual(config.platform, "taobao")
            self.assertEqual(config.appkey, "config_key")
            self.assertEqual(config.keyword, "冰箱")
            self.assertEqual(config.pages, 10)
            self.assertEqual(config.page_size, 30)
        finally:
            os.unlink(config_path)

    def test_load_missing_file(self):
        """测试不存在的配置文件"""
        config = load_from_config_file("nonexistent.json")
        self.assertEqual(config.platform, "")
        self.assertEqual(config.pages, 2)

    def test_load_invalid_json(self):
        """测试无效的 JSON 文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("not valid json")
            config_path = f.name

        try:
            config = load_from_config_file(config_path)
            # 应使用默认值
            self.assertEqual(config.platform, "")
        finally:
            os.unlink(config_path)


class TestValidateConfig(unittest.TestCase):
    """配置验证测试"""

    def test_valid_taobao_config(self):
        """测试有效的淘宝配置"""
        config = Config()
        config.platform = "taobao"
        config.appkey = "valid_key"
        config.secret = "valid_secret"
        config.keyword = "空调"
        config.pages = 5
        config.page_size = 40
        valid, msg = validate_config(config)
        self.assertTrue(valid)

    def test_valid_jd_config(self):
        """测试有效的京东配置"""
        config = Config()
        config.platform = "jd"
        config.appkey = "valid_key"
        config.secret = "valid_secret"
        config.keyword = "手机"
        valid, msg = validate_config(config)
        self.assertTrue(valid)

    def test_invalid_platform(self):
        """测试无效平台"""
        config = Config()
        config.platform = "pdd"
        config.appkey = "k"
        config.secret = "s"
        config.keyword = "k"
        valid, msg = validate_config(config)
        self.assertFalse(valid)
        self.assertIn("不支持", msg)

    def test_empty_appkey(self):
        """测试空 API Key"""
        config = Config()
        config.platform = "taobao"
        config.appkey = ""
        config.secret = "s"
        config.keyword = "k"
        valid, msg = validate_config(config)
        self.assertFalse(valid)
        self.assertIn("API Key", msg)

    def test_empty_secret(self):
        """测试空 Secret"""
        config = Config()
        config.platform = "taobao"
        config.appkey = "k"
        config.secret = ""
        config.keyword = "k"
        valid, msg = validate_config(config)
        self.assertFalse(valid)
        self.assertIn("API Secret", msg)

    def test_empty_keyword(self):
        """测试空关键词"""
        config = Config()
        config.platform = "taobao"
        config.appkey = "k"
        config.secret = "s"
        config.keyword = ""
        valid, msg = validate_config(config)
        self.assertFalse(valid)
        self.assertIn("产品名称", msg)

    def test_invalid_pages(self):
        """测试无效页数"""
        config = Config()
        config.platform = "taobao"
        config.appkey = "k"
        config.secret = "s"
        config.keyword = "k"
        config.pages = 0
        valid, msg = validate_config(config)
        self.assertFalse(valid)

    def test_invalid_page_size(self):
        """测试无效每页数量"""
        config = Config()
        config.platform = "taobao"
        config.appkey = "k"
        config.secret = "s"
        config.keyword = "k"
        config.page_size = 0
        valid, msg = validate_config(config)
        self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()