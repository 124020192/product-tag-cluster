# -*- coding: utf-8 -*-
"""
Flask Web 应用 - 电商产品信息聚合与分析工具
"""
import sys
import os
import json
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, session
from src.config import Config, PLATFORM_NAMES
from src.api_client import APIClient, MockAPIClient
from src.tag_engine import (
    process_tags, extract_candidate_tags, get_item_tags, cluster_products, auto_select_tags,
    display_tags, select_tags_interactive
)
from src.output_formatter import save_to_json, save_raw_items, display_clusters_console
from src.settings_manager import load_settings, save_settings, get_builtin_blacklist, get_builtin_stop_words, get_builtin_synonyms, compute_custom_from_full
from src.search_progress import create_progress, update_progress, set_status, get_progress, remove_progress

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max upload

@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

_search_state = {}


def _run_cluster(items: list, selected_tags: list) -> list:
    return cluster_products(items, selected_tags)


# ====== Routes ======

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search-async", methods=["POST"])
def api_search_async():
    """异步搜索 - 立即返回search_id，前端轮询进度"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400

    search_id = os.urandom(8).hex()
    create_progress(search_id, 4)
    update_progress(search_id, "正在建立搜索连接...", step=1)

    thread = threading.Thread(target=_run_search_async, args=(search_id, data))
    thread.daemon = True
    thread.start()

    return jsonify({"search_id": search_id})


def _run_search_async(search_id: str, config_dict: dict):
    """在后台线程中执行搜索"""
    try:
        config = Config()
        config.platform = config_dict.get("platform", "taobao")
        config.appkey = config_dict.get("appkey", "")
        config.secret = config_dict.get("secret", "")
        config.keyword = config_dict.get("keyword", "")
        config.pages = int(config_dict.get("pages", 2))
        config.page_size = int(config_dict.get("page_size", 40))
        config.output_format = "json"
        config.output_dir = os.path.join(os.path.dirname(__file__), "..", "output")

        api_quota = int(config_dict.get("api_quota", 10))
        is_mock = config_dict.get("mock", False)

        update_progress(search_id, f"正在搜索【{config.keyword}】...", step=2)

        if is_mock:
            client = MockAPIClient(config)
        else:
            client = APIClient(config)

        items = client.search()

        if not items:
            update_progress(search_id, "未搜索到商品数据", step=4)
            set_status(search_id, "error")
            return

        update_progress(search_id, f"获取到 {len(items)} 条商品，正在提取标签...", step=3)

        tags = process_tags(items, keyword=config.keyword)
        candidate_dict = extract_candidate_tags(items, keyword=config.keyword)
        candidate_tags = [{"name": k, "count": v} for k, v in candidate_dict.items()]

        actual_calls = getattr(client, "api_calls", 0)

        _search_state[search_id] = {
            "items": items,
            "tags": tags,
            "candidate_tags": candidate_tags,
            "selected_tags": [],
            "clusters": [],
            "total_products": len(items),
            "keyword": config.keyword,
            "platform_name": PLATFORM_NAMES.get(config.platform, config.platform),
            "api_calls": actual_calls,
            "api_quota": api_quota,
            "pages": config.pages,
        }

        update_progress(search_id, f"搜索完成！共 {len(tags)} 个标签", step=4)
        set_status(search_id, "complete")

    except Exception as e:
        update_progress(search_id, f"错误: {str(e)}")
        set_status(search_id, "error")


@app.route("/api/search-result/<search_id>")
def api_search_result(search_id):
    """获取搜索结果（异步搜索完成后调用）"""
    if search_id not in _search_state:
        return jsonify({"error": "会话已过期或搜索尚未完成"}), 404
    state = _search_state[search_id]
    remove_progress(search_id)
    return jsonify({
        "search_id": search_id,
        "total_products": state["total_products"],
        "tags": state["tags"],
        "tag_count": len(state["tags"]),
        "candidate_tags": state.get("candidate_tags", []),
        "candidate_count": len(state.get("candidate_tags", [])),
        "keyword": state["keyword"],
        "platform_name": state["platform_name"],
        "api_calls": state["api_calls"],
        "api_quota": state["api_quota"],
        "pages": state["pages"],
    })


@app.route("/api/progress/<search_id>")
def api_progress(search_id):
    """获取搜索进度"""
    return jsonify(get_progress(search_id))


@app.route("/api/upload-tags", methods=["POST"])
def api_upload_tags():
    if 'file' not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "文件名为空"}), 400
    try:
        content = file.read().decode('utf-8').strip()
        tags = []
        if content.startswith('['):
            try:
                tags = json.loads(content)
                if not isinstance(tags, list):
                    tags = []
            except json.JSONDecodeError:
                tags = []
        else:
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('//'):
                    tags.append(line)
        if not tags:
            return jsonify({"error": "未能从文件中解析出有效标签"}), 400
        return jsonify({"tags": tags, "tag_count": len(tags)})
    except Exception as e:
        return jsonify({"error": f"文件解析失败: {str(e)}"}), 500


@app.route("/api/cluster", methods=["POST"])
def api_cluster():
    data = request.get_json()
    search_id = data.get("search_id")
    selected_indices = data.get("selected_indices", [])
    if not search_id or search_id not in _search_state:
        return jsonify({"error": "搜索会话已过期，请重新搜索"}), 400
    state = _search_state[search_id]
    tags = state["tags"]
    tag_list = list(tags.keys())
    if selected_indices == "all":
        selected_tags = tag_list
    else:
        selected_tags = [tag_list[i] for i in selected_indices if 0 <= i < len(tag_list)]
    if not selected_tags:
        selected_tags = tag_list
    state["selected_tags"] = selected_tags
    clusters = _run_cluster(state["items"], selected_tags)
    state["clusters"] = clusters

    cluster_list = []
    for c in clusters:
        rep = c.get("representative", {})
        products_preview = []
        for item in c.get("products", []):
            products_preview.append({
                "num_iid": item.get("num_iid", ""),
                "title": item.get("title", ""),
                "price": item.get("price", "0"),
                "sales": item.get("sales", 0),
                "shop_name": item.get("shop_name", ""),
                "detail_url": item.get("detail_url", ""),
                "pic_url": item.get("pic_url", ""),
                "props_name": item.get("props_name", ""),
                "category_name": item.get("category_name", ""),
                "cat_name": item.get("cat_name", ""),
            })
        cluster_list.append({
            "type_id": c["type_id"],
            "product_count": c["product_count"],
            "tags": c["tags"],
            "tag_display": " | ".join(c["tags"]),
            "price_min": round(c["price_range"]["min"], 2),
            "price_max": round(c["price_range"]["max"], 2),
            "price_avg": round(c["price_range"]["avg"], 2),
            "total_sales": c["total_sales"],
            "is_low_sample": c.get("is_low_sample", False),
            "representative": {
                "num_iid": rep.get("num_iid", "") if rep else "",
                "title": rep.get("title", "无") if rep else "无",
                "shop": rep.get("shop_name", "") if rep else "",
                "price": rep.get("price", "0") if rep else "0",
                "sales": rep.get("sales", 0) if rep else 0,
                "url": rep.get("detail_url", "") if rep else "",
                "pic_url": rep.get("pic_url", "") if rep else "",
                "props_name": rep.get("props_name", "") if rep else "",
                "category_name": rep.get("category_name", "") if rep else "",
                "cat_name": rep.get("cat_name", "") if rep else "",
            } if rep else None,
            "products_preview": products_preview,
        })
    return jsonify({
        "clusters": cluster_list,
        "total_types": len(clusters),
        "total_products": state["total_products"],
        "selected_tags": selected_tags,
        "keyword": state["keyword"],
        "platform_name": state["platform_name"],
    })


@app.route("/api/export", methods=["POST"])
def api_export():
    data = request.get_json()
    search_id = data.get("search_id")
    if not search_id or search_id not in _search_state:
        return jsonify({"error": "会话已过期"}), 400
    state = _search_state[search_id]
    if not state["clusters"]:
        return jsonify({"error": "请先执行聚类分析"}), 400
    try:
        config = Config()
        config.keyword = state["keyword"]
        config.platform = "taobao"
        config.output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        filepath = save_to_json(config, state["clusters"], state["selected_tags"], state["total_products"])
        return jsonify({"filepath": filepath})
    except Exception as e:
        return jsonify({"error": f"导出失败: {str(e)}"}), 500


@app.route("/api/export/raw", methods=["POST"])
def api_export_raw():
    data = request.get_json()
    search_id = data.get("search_id")
    if not search_id or search_id not in _search_state:
        return jsonify({"error": "会话已过期"}), 400
    state = _search_state[search_id]
    if not state["items"]:
        return jsonify({"error": "无商品数据可导出"}), 400
    try:
        config = Config()
        config.keyword = state["keyword"]
        config.platform = "taobao"
        config.pages = state.get("pages", 2)
        config.page_size = 40
        config.output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        filepath = save_raw_items(state["items"], config)
        return jsonify({"filepath": filepath})
    except Exception as e:
        return jsonify({"error": f"导出失败: {str(e)}"}), 500


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(load_settings())


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    builtin_bl = get_builtin_blacklist()
    builtin_sw = get_builtin_stop_words()
    builtin_syn = get_builtin_synonyms()
    full_blacklist = data.get("custom_blacklist", [])
    full_stop_words = data.get("custom_stop_words", [])
    full_synonyms = data.get("custom_synonyms", {})
    custom_blacklist = compute_custom_from_full(full_blacklist, builtin_bl)
    custom_stop_words = compute_custom_from_full(full_stop_words, builtin_sw)
    custom_synonyms = {}
    for k, v in full_synonyms.items():
        k = k.strip()
        v = v.strip()
        if k and v and (k not in builtin_syn or builtin_syn[k] != v):
            custom_synonyms[k] = v
    to_save = {
        "custom_blacklist": custom_blacklist,
        "custom_stop_words": custom_stop_words,
        "custom_synonyms": custom_synonyms,
    }
    if save_settings(to_save):
        return jsonify({"status": "ok", "message": "设置已保存"})
    return jsonify({"error": "保存失败"}), 500


@app.route("/api/settings/blacklist", methods=["GET"])
def api_get_blacklist():
    from src.tag_engine import GENERIC_WORDS, STOP_WORDS, SYNONYM_MAP
    return jsonify({
        "builtin_blacklist": sorted(GENERIC_WORDS),
        "builtin_stop_words": sorted(STOP_WORDS),
        "builtin_synonyms": SYNONYM_MAP,
        "custom": load_settings(),
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  电商产品信息聚合与分析工具 - Web版")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)