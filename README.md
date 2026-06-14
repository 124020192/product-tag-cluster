<div align="center">

# 🔍 电商产品信息聚合与分析工具

**Product Tag Cluster — 基于标签聚类的电商产品智能分析平台**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000.svg?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-00ACD7.svg?style=for-the-badge)](LICENSE)

输入 API 凭证和产品名称，自动搜索商品 → 提取标签特征 → 聚类分析产品类型 → 输出结构化结果

> [English](#english) | 简体中文

---

</div>

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🏪 **多平台支持** | 淘宝/天猫、京东，通过万邦 Onebound API 对接 |
| 🏷️ **智能标签提取** | 从商品标题 + 属性参数提取特征标签，同义词合并 + 通用词过滤 |
| 🎯 **交互式标签选择** | 可视化展示市场标签分布，用户自定义筛选关注维度 |
| 🧩 **产品类型聚类** | 基于标签组合自动聚类，识别品类下不同产品类型并编号 |
| 📊 **多格式输出** | 控制台展示 + JSON / CSV 文件导出 |
| 🌐 **Web 可视化界面** | 响应式 Web 应用，支持返回上一步、API 配额管理 |
| 🛡️ **模拟演示模式** | 无需真实 API 即可体验全部功能 |
| ⚡ **API 消耗优化** | 智能分页策略，默认 2 次调用即可分析 80 条商品 |

---

## 🚀 快速开始

### 安装依赖

```bash
git clone https://github.com/124020192/product-tag-cluster.git
cd product-tag-cluster

# 核心依赖（仅标准库即可运行 CLI）
# Flask 仅 Web UI 需要
pip install flask
```

### 方式一：Web 界面（推荐）

**Windows 用户**：双击 `启动网页版.bat`

**手动启动**：
```bash
cd web
python app.py
# 浏览器打开 http://127.0.0.1:5000
```

### 方式二：命令行界面

```bash
# 交互式模式（推荐新手）
python product_monster.py

# 模拟演示模式（无需 API）
python product_monster.py --mock --batch

# 命令行参数模式
python product_monster.py \
    --platform taobao \
    --appkey YOUR_APPKEY \
    --secret YOUR_SECRET \
    --keyword 空调 \
    --pages 2

# 配置文件模式
python product_monster.py --config config.json
```

---

## 📖 工作流程

```
用户输入：API 凭证 + 平台 + 产品名称
        │
        ▼
  调用平台 API 搜索商品
        │
        ▼
  提取所有商品的标签信息
        │
        ▼
  展示市场标签统计（用户自定义选择）
        │
        ▼
  基于标签组合聚类 → 产品类型编号
        │
        ▼
  控制台输出 + JSON/CSV 文件导出
```

---

## 📁 项目结构

```
product-tag-cluster/
├── product_monster.py              # CLI 入口
├── config.json                     # 配置文件
├── 启动网页版.bat                   # Windows 双击启动脚本
├── src/                            # 核心模块
│   ├── config.py                   #   配置管理
│   ├── api_client.py               #   万邦 API 客户端 + Mock 模拟
│   ├── tag_engine.py               #   标签提取 / 同义词合并 / 聚类引擎
│   └── output_formatter.py         #   输出格式化（Console / JSON / CSV）
├── web/                            # Flask Web 应用
│   ├── app.py                      #   后端 API 路由
│   ├── templates/index.html        #   前端界面
│   └── static/                     #   静态资源
├── tests/                          # 单元测试（49 个用例）
│   ├── test_config.py
│   ├── test_tag_engine.py
│   └── test_api_client.py
├── output/                         # 分析结果输出目录
├── onebound-api-sdk/               # 万邦 PHP SDK 参考
└── 电商产品信息聚合工具_PRD_V1.0.md  # 产品需求文档
```

---

## 🔧 配置

编辑 `config.json`：

```json
{
    "platform": "taobao",
    "appkey": "你的 API Key",
    "secret": "你的 API Secret",
    "keyword": "空调",
    "pages": 2,
    "page_size": 40,
    "output_format": "json",
    "output_dir": "./output"
}
```

> **API 配额说明**：默认每次搜索消耗 **2 次 API 调用**（2 页 × 40 条/页 = 80 条商品）。在 Web 界面中可设置 API 调用上限，防止超额。

---

## 🧪 运行测试

```bash
python -m unittest discover tests -v
```

---

## 📊 输出示例

```
════════════════════════════════════════════════════════
  空调 -- 产品类型分析结果
  平台：淘宝
════════════════════════════════════════════════════════
  共 80 条商品，聚类为 5 种产品类型

────────────────────────────────────────────────────────
  类型 #1（45 个商品）
    特征：壁挂式 | 变频 | 1.5匹 | 一级能效
    价格区间：2499 元 - 3899 元
    代表商品：格力云佳 1.5匹 新一级能效 变频冷暖 壁挂式空调
    店铺：格力官方旗舰店
```

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| Web 框架 | Flask |
| API | 万邦 Onebound API（淘宝/京东商品搜索） |
| 测试 | Python unittest（49 个测试用例） |
| 前端 | 原生 HTML/CSS/JS（响应式设计） |

---

## 📄 License

本项目使用 [MIT License](LICENSE)。

---

<div align="center">
  <b>⭐ 如果这个项目对你有帮助，请给一个 Star！</b>
</div>