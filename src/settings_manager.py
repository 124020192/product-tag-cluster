# -*- coding: utf-8 -*-
"""
设置管理模块 - 管理用户自定义的黑名单、停用词、同义词映射
支持持久化保存到 JSON 文件
"""
import json
import os
from typing import Optional

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_settings.json")

# 默认空设置
DEFAULT_SETTINGS = {
    "custom_blacklist": [],
    "custom_stop_words": [],
    "custom_synonyms": {},
}


def load_settings() -> dict:
    """加载用户自定义设置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 确保有所有字段
                for k in DEFAULT_SETTINGS:
                    if k not in data:
                        data[k] = DEFAULT_SETTINGS[k]
                return data
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> bool:
    """保存用户自定义设置"""
    try:
        # 只保存我们关心的字段
        to_save = {}
        for k in DEFAULT_SETTINGS:
            to_save[k] = settings.get(k, DEFAULT_SETTINGS[k])
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Settings] 保存设置失败: {e}")
        return False


def add_to_blacklist(words: list[str]) -> bool:
    """添加词到黑名单"""
    s = load_settings()
    existing = set(s["custom_blacklist"])
    for w in words:
        w = w.strip()
        if w:
            existing.add(w)
    s["custom_blacklist"] = sorted(existing)
    return save_settings(s)


def remove_from_blacklist(words: list[str]) -> bool:
    """从黑名单移除词"""
    s = load_settings()
    existing = set(s["custom_blacklist"])
    for w in words:
        existing.discard(w.strip())
    s["custom_blacklist"] = sorted(existing)
    return save_settings(s)


def get_merged_blacklist() -> set[str]:
    """获取合并后的黑名单（内置 + 自定义）"""
    from .tag_engine import GENERIC_WORDS
    s = load_settings()
    return GENERIC_WORDS | set(s["custom_blacklist"])


def get_merged_stop_words() -> set[str]:
    """获取合并后的停用词（内置 + 自定义）"""
    from .tag_engine import STOP_WORDS
    s = load_settings()
    return STOP_WORDS | set(s["custom_stop_words"])


def get_builtin_blacklist() -> set[str]:
    """获取内置黑名单"""
    from .tag_engine import GENERIC_WORDS
    return set(GENERIC_WORDS)


def get_builtin_stop_words() -> set[str]:
    """获取内置停用词"""
    from .tag_engine import STOP_WORDS
    return set(STOP_WORDS)


def get_builtin_synonyms() -> dict:
    """获取内置同义词映射"""
    from .tag_engine import SYNONYM_MAP
    return dict(SYNONYM_MAP)


def compute_custom_from_full(full_list: list[str], builtin_set: set[str]) -> list[str]:
    """从完整列表中计算出自定义部分（不在内置列表中的就是自定义的）"""
    return sorted(set(full_list) - builtin_set)


def get_merged_synonyms() -> dict:
    """获取合并后的同义词映射（内置 + 自定义）"""
    from .tag_engine import SYNONYM_MAP
    s = load_settings()
    merged = dict(SYNONYM_MAP)
    merged.update(s["custom_synonyms"])
    return merged