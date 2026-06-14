# -*- coding: utf-8 -*-
"""
API 客户端模块 - 对接万邦 API，搜索商品数据
优化：尽可能节省 API 调用次数
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional
from .config import Config, PLATFORM_NAMES


class APIClient:
    """万邦 API 客户端 - 优化版，最小化 API 调用"""

    def __init__(self, config: Config):
        self.config = config
        # base_url example: "https://api-gw.onebound.cn/taobao/"
        self.base_url = config.get_api_base_url()
        self.api_type = config.get_search_api_type()
        self.request_interval = 0.5
        self.timeout = 8
        self.max_retries = 3
        self.api_calls = 0
        self.last_error = ""  # 存储最后一次API错误信息

    def _build_request_url(self, page: int, page_size: int) -> str:
        """构建请求 URL，例如：
        https://api-gw.onebound.cn/taobao/item_search/?key=xxx&q=空调&page=1&page_size=40
        """
        # base_url 已经包含末尾 /，例如 "https://api-gw.onebound.cn/taobao/"
        # api_type = "item_search"
        base = self.base_url.rstrip("/")  # "https://api-gw.onebound.cn/taobao"
        # 构建: https://api-gw.onebound.cn/taobao/item_search/
        url_prefix = f"{base}/{self.api_type}/"

        params = {
            "key": self.config.appkey,
            "secret": self.config.secret,
            "q": self.config.keyword,
            "page": str(page),
            "page_size": str(page_size),
            "lang": "zh-CN",
            "result_type": "json",
            "cache": "yes",
        }
        url = f"{url_prefix}?{urllib.parse.urlencode(params)}"
        return url

    def _make_request(self, url: str) -> Optional[dict]:
        """发起 HTTP 请求，带重试机制"""
        # 确保 URL 是纯 ASCII - 对非ASCII字符做百分号编码
        # 修复 Python 3.13 + Windows 下 urllib 的 UnicodeEncodeError
        encoded_url = ""
        i = 0
        while i < len(url):
            if url[i] == '%' and i + 2 < len(url) and all(c in '0123456789ABCDEFabcdef' for c in url[i+1:i+3]):
                encoded_url += url[i:i+3]
                i += 3
            elif ord(url[i]) < 128:
                encoded_url += url[i]
                i += 1
            else:
                for b in url[i].encode('utf-8'):
                    encoded_url += f'%{b:02X}'
                i += 1
        url = encoded_url

        # 打印调试信息
        print(f"  [Debug] 最终请求 URL (前150字符): {url[:150]}")

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data = response.read().decode("utf-8")
                    result = json.loads(data)
                    self.api_calls += 1
                    return result
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if attempt < self.max_retries:
                    print(f"[Warning] 接口返回错误 ({last_error})，正在进行第 {attempt} 次重试...")
                    time.sleep(self.request_interval)
                else:
                    print(f"[Error] 接口返回错误 ({last_error})，重试已达上限")
            except urllib.error.URLError as e:
                last_error = str(e.reason)
                if attempt < self.max_retries:
                    print(f"[Warning] 接口请求超时或网络错误，正在进行第 {attempt} 次重试...")
                    time.sleep(self.request_interval)
                else:
                    print(f"[Error] 接口连续 {self.max_retries} 次失败: {last_error}")
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {e}"
                if attempt < self.max_retries:
                    print(f"[Warning] 响应数据解析失败，正在进行第 {attempt} 次重试...")
                    time.sleep(self.request_interval)
                else:
                    print(f"[Error] 响应数据解析失败: {e}")
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    print(f"[Warning] 请求异常 ({last_error})，正在进行第 {attempt} 次重试...")
                    time.sleep(self.request_interval)
                else:
                    print(f"[Error] 请求异常: {last_error}")
        return None

    def _normalize_item(self, item: dict) -> Optional[dict]:
        """标准化商品数据"""
        try:
            normalized = {
                "platform": self.config.platform,
                "platform_name": PLATFORM_NAMES.get(self.config.platform, self.config.platform),
                "num_iid": item.get("num_iid", ""),
                "title": item.get("title", ""),
                "price": item.get("price", "0"),
                "sales": item.get("sales", 0) or item.get("volume", 0) or 0,
                "shop_name": item.get("shop_name", "") or item.get("nick", ""),
                "detail_url": item.get("detail_url", ""),
                "pic_url": item.get("pic_url", ""),
                "props_name": item.get("props_name", ""),
                "props_list": item.get("props_list", []),
                "seller_info": item.get("seller_info", {}),
                "category_name": item.get("category_name", ""),
                "cat_name": item.get("cat_name", ""),
            }
            if isinstance(normalized["props_list"], str):
                normalized["props_list"] = [
                    p.strip() for p in normalized["props_list"].split(";") if p.strip()
                ]
            elif not isinstance(normalized["props_list"], list):
                normalized["props_list"] = []
            return normalized
        except Exception as e:
            print(f"[Warning] 商品数据标准化失败: {e}")
            return None

    def _parse_response(self, response: dict) -> tuple[list[dict], int]:
        """解析 API 响应，返回 (商品列表, 总结果数)
        
        万邦 API item_search 返回格式：
        {
          "items": {"item": [{...}, ...]},
          "total_results": 100,
          ...
        }
        """
        items = []
        if not response:
            return items, 0

        # 检查错误
        error = response.get("error", "")
        error_code = response.get("error_code", "")
        if error:
            print(f"[Error] API 返回错误: [{error_code}] {error}")
            return items, 0

        total_results = 0
        try:
            total_results = int(response.get("total_results", 0))
        except (ValueError, TypeError):
            total_results = 0

        # 从 items 字段提取商品列表
        # 响应结构: items → {"item": [{...}, ...]}
        items_container = response.get("items", {})
        if not items_container:
            items_container = {}

        # items_container 可能是一个 dict 包含 "item" 键，也可能是列表
        if isinstance(items_container, dict):
            item_list = items_container.get("item", [])
        elif isinstance(items_container, list):
            item_list = items_container
        else:
            item_list = []

        if not isinstance(item_list, list):
            item_list = []

        for raw_item in item_list:
            normalized = self._normalize_item(raw_item)
            if normalized:
                items.append(normalized)

        return items, total_results

    def search(self) -> list[dict]:
        """智能搜索 - 最小化 API 调用"""
        all_items = []
        keyword = self.config.keyword
        platform_name = PLATFORM_NAMES.get(self.config.platform, self.config.platform)
        max_pages = self.config.pages
        page_size = self.config.page_size

        print(f"\n[搜索] 正在搜索【{keyword}】，平台：{platform_name}")
        print(f"  每页 {page_size} 条，最大 {max_pages} 页，使用缓存加速")

        # 先请求第1页，查看总结果数
        url = self._build_request_url(1, page_size)
        print(f"  请求 URL: {url[:120]}...")
        print(f"  请求第 1 页...")

        response = self._make_request(url)
        if not response:
            print("  [Error] 第 1 页请求失败，搜索终止")
            return []

        # 检查 API 返回的错误
        if response.get("error"):
            err_msg = response.get("error", "")
            err_reason = response.get("reason", "")
            full_err = f"{err_msg} {err_reason}".strip()
            print(f"  [Error] API 返回错误: {full_err}")
            return []

        items_page1, total_results = self._parse_response(response)
        all_items.extend(items_page1)

        items_count = len(all_items)
        print(f"  [OK] 第 1 页完成，API 返回总结果数：{total_results}，已获取 {items_count} 条")

        # 智能判断是否需要更多页
        if total_results > 0 and items_count < total_results and max_pages > 1:
            total_pages = min(max_pages, (total_results + page_size - 1) // page_size)
            actual_pages = min(total_pages, max_pages)

            if actual_pages > 1:
                print(f"  数据还有更多，继续获取第 2-{actual_pages} 页（共 {actual_pages-1} 次调用）")

            for page in range(2, actual_pages + 1):
                url = self._build_request_url(page, page_size)
                print(f"  请求第 {page}/{actual_pages} 页...")

                response = self._make_request(url)
                if not response:
                    print(f"  [Warning] 第 {page} 页请求失败，跳过")
                    continue

                if response.get("error"):
                    print(f"  [Warning] 第 {page} 页 API 返回错误: {response.get('error')}，跳过")
                    continue

                items_page, _ = self._parse_response(response)
                all_items.extend(items_page)
                print(f"  [OK] 第 {page}/{actual_pages} 页完成，累计 {len(all_items)} 条")

                if page < actual_pages:
                    time.sleep(self.request_interval)
        else:
            if total_results == 0:
                print(f"  第 1 页已获取全部数据，无需更多请求")
            elif items_count == 0:
                print(f"  [Warning] 未能获取到商品数据")

        print(f"\n[完成] 搜索完成，共获取 {len(all_items)} 条商品数据（API 调用次数：{self.api_calls}）")
        return all_items


class MockAPIClient(APIClient):
    """模拟 API 客户端（用于测试和演示，不消耗 API）"""

    def __init__(self, config: Config):
        super().__init__(config)

    def _generate_mock_items(self, page: int) -> list[dict]:
        """生成模拟商品数据"""
        import random

        items = []
        base_keyword = self.config.keyword

        product_types = [
            {"title_prefix": "格力云佳", "shop": "格力官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "一级能效", "冷暖型", "自清洁", "智能控制"]},
            {"title_prefix": "美的极酷", "shop": "美的官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "三级能效", "冷暖型"]},
            {"title_prefix": "海尔静悦", "shop": "海尔官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "一级能效", "冷暖型", "自清洁"]},
            {"title_prefix": "格力云逸", "shop": "格力官方旗舰店", "props": ["立柜式", "变频", "3匹", "一级能效", "冷暖型"]},
            {"title_prefix": "美的智行", "shop": "美的官方旗舰店", "props": ["立柜式", "变频", "2匹", "一级能效", "冷暖型"]},
            {"title_prefix": "华凌", "shop": "华凌官方旗舰店", "props": ["壁挂式", "定频", "1.5匹", "冷暖型"]},
            {"title_prefix": "格力冷静王", "shop": "格力官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "一级能效", "冷暖型", "新风空调"]},
            {"title_prefix": "TCL", "shop": "TCL官方旗舰店", "props": ["立柜式", "变频", "3匹", "冷暖型"]},
            {"title_prefix": "奥克斯", "shop": "奥克斯官方旗舰店", "props": ["壁挂式", "定频", "1.5匹", "单冷型"]},
            {"title_prefix": "美的移动空调", "shop": "美的官方旗舰店", "props": ["移动空调", "变频", "1匹", "冷暖型"]},
            {"title_prefix": "海尔中央空调", "shop": "海尔中央空调旗舰店", "props": ["中央空调", "变频", "3匹", "一级能效", "冷暖型"]},
            {"title_prefix": "小米空调", "shop": "小米官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "一级能效", "智能控制", "冷暖型"]},
            {"title_prefix": "格力云锦", "shop": "格力官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "一级能效", "智能控制", "自清洁", "冷暖型"]},
            {"title_prefix": "美的风尊", "shop": "美的官方旗舰店", "props": ["壁挂式", "变频", "1.5匹", "一级能效", "冷暖型", "智能控制"]},
        ]

        for i in range(self.config.page_size):
            pt = random.choice(product_types)
            price = random.randint(1899, 8999)
            sales = random.randint(100, 50000)
            suffix = random.choice(["", " (2024新款)", " (大1匹)", " 三级能效"])
            title = f"{pt['title_prefix']} {base_keyword} {price}元{suffix}"
            if page == 1 and i == 0:
                title = f"{pt['title_prefix']} {base_keyword}"

            item = {
                "num_iid": f"{page}{i+1:04d}",
                "title": title,
                "price": str(price),
                "sales": sales,
                "shop_name": pt["shop"],
                "nick": pt["shop"],
                "detail_url": f"https://item.taobao.com/item.htm?id={page}{i+1:04d}",
                "pic_url": f"https://img.example.com/{page}{i+1:04d}.jpg",
                "props_name": ";".join(pt["props"]),
                "props_list": pt["props"],
                "category_name": "家用电器 > 空调",
                "cat_name": "空调",
                "seller_info": {"shop_name": pt["shop"], "score": 4.8},
            }
            items.append(item)
        return items

    def search(self) -> list[dict]:
        """模拟搜索（不消耗 API）"""
        all_items = []
        total_pages = self.config.pages
        keyword = self.config.keyword
        platform_name = PLATFORM_NAMES.get(self.config.platform, self.config.platform)

        print(f"\n[搜索-模拟模式] 正在搜索【{keyword}】，平台：{platform_name}，共 {total_pages} 页...")

        for page in range(1, total_pages + 1):
            items = self._generate_mock_items(page)
            all_items.extend(items)
            print(f"  [OK] 第 {page}/{total_pages} 页完成，累计 {len(all_items)} 条")

        print(f"\n[完成-模拟模式] 搜索完成，共获取 {len(all_items)} 条商品数据（0 次 API 调用）")
        return all_items