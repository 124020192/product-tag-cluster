# -*- coding: utf-8 -*-
"""
搜索进度跟踪模块 - 存储和获取搜索进度信息
"""
import time
from collections import OrderedDict

# 进度存储：{search_id: {messages: [], current: 0, total: 0, status: ""}}
_progress_store: dict = {}
_max_store = 50  # 最多保留50条进度记录


def create_progress(search_id: str, total_steps: int = 4):
    """创建新的进度跟踪"""
    _progress_store[search_id] = {
        "messages": [],
        "current": 0,
        "total": total_steps,
        "status": "starting",
        "percent": 0,
        "updated_at": time.time(),
    }
    # 清理旧记录
    while len(_progress_store) > _max_store:
        _progress_store.pop(next(iter(_progress_store)), None)


def update_progress(search_id: str, message: str, step: int = None, total: int = None):
    """更新进度"""
    p = _progress_store.get(search_id)
    if not p:
        return
    if step is not None:
        p["current"] = step
    else:
        p["current"] += 1
    if total is not None:
        p["total"] = total
    p["messages"].append({"msg": message, "time": time.strftime("%H:%M:%S")})
    p["percent"] = round((p["current"] / p["total"]) * 100) if p["total"] > 0 else 0
    p["updated_at"] = time.time()


def set_status(search_id: str, status: str):
    """设置状态（starting/running/complete/error）"""
    p = _progress_store.get(search_id)
    if p:
        p["status"] = status
        p["updated_at"] = time.time()


def get_progress(search_id: str) -> dict:
    """获取进度信息"""
    p = _progress_store.get(search_id)
    if not p:
        return {"messages": [], "current": 0, "total": 0, "status": "not_found", "percent": 0}
    return p


def remove_progress(search_id: str):
    """移除进度记录"""
    _progress_store.pop(search_id, None)