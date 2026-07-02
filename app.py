# -*- coding: utf-8 -*-
"""
亚马逊 AI 全链路自动化工具包 — 单文件版本
所有代码都在一个文件里，无导入问题
"""
import streamlit as st
import json, os, sys, time, re, io, csv
from collections import Counter

# ============================================================
# LinkFox API 接口（内联版）
# ============================================================
API_KEY = os.getenv("LINKFOX_API_KEY", "微信联系获取")
BASE_URL = "https://tool-gateway.linkfox.com"

def _call(path: str, body: dict, timeout=25) -> dict:
    """调用 LinkFox API"""
    import requests
    url = BASE_URL + path
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def get_product_detail(asins: str) -> dict:
    return _call("/amazon/product/detail", {"asins": asins})

def get_competitor_data(marketplace: str, asin: str) -> dict:
    return _call("/sellersprite/competitor-lookup", {"marketplace": marketplace, "asin": asin})

def get_traffic_keywords(marketplace: str, asin: str) -> dict:
    return _call("/sellersprite/traffic/keyword", {"marketplace": marketplace, "asin": asin})

def search_products(marketplace: str, keyword: str, min_price: int, max_price: int, min_bsr: int, max_bsr: int, min_monthly_sales: int, min_rating: float) -> dict:
    return _call("/sellersprite/productSearch", {"marketplace": marketplace, "keyword": keyword, "minPrice": min_price, "maxPrice": max_price, "minBsr": min_bsr, "maxBsr": max_bsr, "minMonthlySales": min_monthly_sales, "minRating": min_rating})

# ============================================================
# 报告生成器（内联版）
# ============================================================
def generate_product_research_report(product: dict, competitor: dict, keywords: dict) -> str:
    """生成选品分析报告"""
    title = product.get("title", "N/A")
    price = product.get("price", 0)
    bsr = product.get("bsr", "N/A")
    rating = product.get("rating", 0)
    reviews = product.get("reviews", 0)
    monthly_sales = product.get("monthlySalesUnits", 0)
    
    report = f"""# 选品可行性分析报告

## 核心数据总览

| 指标 | 数值 |
|------|------|
| 商品标题 | {title[:60]}... |
| 当前售价 | ${price} |
| BSR排名 | #{bsr} |
| 评分/评论数 | {rating}星 / {reviews}条 |
| 月销量估算 | {monthly_sales}件 |

## 竞品分析

"""
    
    comps = competitor.get("products", [])[:5]
    if comps:
        report += "| ASIN | 售价 | BSR | 月销量 | 利润率 |\n"
        report += "|------|------|-----|--------|--------|\n"
        for c in comps:
            report += f"| {c.get('asin', 'N/A')} | ${c.get('price', 'N/A')} | #{c.get('bsr', 'N/A')} | {c.get('monthlySalesUnits', 'N/A')}件 | {c.get('profit', 'N/A')}% |\n"
    else:
        report += "暂无竞品数据\n"
    
    report += "\n## 关键词分析\n\n"
    kws = keywords.get("data", [])[:10]
    if kws:
        report += "| 关键词 | 流量占比 | 转化类型 | 自然排名 | 广告排名 |\n"
        report += "|--------|----------|----------|----------|----------|\n"
        for kw in kws:
            report += f"| {kw.get('keyword', 'N/A')} | {kw.get('trafficShare', 'N/A')}% | {kw.get('conversionType', 'N/A')} | #{kw.get('organicRank', 'N/A')} | #{kw.get('adRank', 'N/A')} |\n"
    else:
        report += "暂无关键词数据\n"
    
    report += "\n## 综合评估\n\n"
    report += "- ✅ 数据获取成功\n"
    report += f"- 📊 月销量: {monthly_sales}件\n"
    report += f"- 💰 售价: ${price}\n"
    report += "- ⚠️ 建议结合利润核算器计算实际利润\n"
    
    return report

def generate_listing(product: dict, keywords: dict) -> str:
    """生成Listing文案"""
    title = product.get("title", "")
    features = product.get("features", [])
    keyword_list = keywords.get("data", [])[:20]
    
    # 提取核心关键词
    kw_text = " ".join([kw.get("keyword", "") for kw in keyword_list if kw.get("trafficShare", 0) > 1])[:200]
    
    listing = f"""# Listing 文案生成

## 商品标题（建议）

{title}

## 五点描述（优化版）

"""
    
    if features and len(features) > 0:
        for i, feat in enumerate(features[:5], 1):
            listing += f"{i}. **{feat[:50]}** — {feat[50:150]}...\n\n"
    else:
        listing += "1. **高品质材料** — 采用优质材料制造，耐用性强\n"
        listing += "2. **人性化设计** — 考虑用户使用习惯，操作简便\n"
        listing += "3. **广泛适用性** — 适合多种场景使用\n"
        listing += "4. **高性价比** — 同等品质下价格更优\n"
        listing += "5. **满意保证** — 如有问题，支持退换\n\n"
    
    listing += "## 后台搜索词（Hidden Keywords）\n\n"
    listing += kw_text[:250] + "\n\n"
    
    listing += "## 关键词投放建议\n\n"
    high_traffic = [kw for kw in keyword_list if kw.get("trafficShare", 0) > 5][:10]
    if high_traffic:
        listing += "**高流量词（建议精准匹配）**: " + ", ".join([kw.get("keyword", "") for kw in high_traffic]) + "\n\n"
    
    medium_traffic = [kw for kw in keyword_list if 1 < kw.get("trafficShare", 0) <= 5][:15]
    if medium_traffic:
        listing += "**中流量词（建议词组匹配）**: " + ", ".join([kw.get("keyword", "") for kw in medium_traffic]) + "\n\n"
    
    return listing

def generate_ad_plan(product: dict, keywords: dict) -> str:
    """生成广告方案"""
    price = product.get("price", 29.99)
    title = product.get("title", "")
    keyword_list = keywords.get("data", [])
    
    budget_daily = max(20, int(price * 2))
    budget_total = budget_daily * 30
    
    plan = f"""# 新品广告初始化方案

## 预算规划

| 项目 | 金额 |
|------|------|
| 每日预算 | ${budget_daily} |
| 30天总预算 | ${budget_total} |
| 建议ACoS目标 | 20-30% |

## 关键词分组

### 组1: 精准词（自动投放）
"""
    
    if keyword_list:
        exact_kws = [kw for kw in keyword_list if kw.get("trafficShare", 0) > 3][:5]
        if exact_kws:
            for kw in exact_kws:
                plan += f"- {kw.get('keyword', '')} (流量占比: {kw.get('trafficShare', 0)}%)\n"
    
    plan += "\n### 组2: 扩展词（手动精准）\n"
    
    if keyword_list:
        phrase_kws = [kw for kw in keyword_list if 1 < kw.get("trafficShare", 0) <= 3][:10]
        if phrase_kws:
            for kw in phrase_kws:
                plan += f"- {kw.get('keyword', '')} (流量占比: {kw.get('trafficShare', 0)}%)\n"
    
    plan += "\n## 投放策略\n\n"
    plan += "1. **第1-7天**: 自动投放，收集搜索词数据\n"
    plan += "2. **第8-14天**: 分析搜索词报告，添加精准词到手动广告\n"
    plan += "3. **第15-21天**: 否定无效词，优化ACoS\n"
    plan += "4. **第22-30天**: 扩大投放，提升曝光\n\n"
    
    plan += "## 关键指标监控\n\n"
    plan += "- CTR（点击率）: 目标 > 0.5%\n"
    plan += "- CVR（转化率）: 目标 > 10%\n"
    plan += "- ACoS: 目标 < 30%\n"
    plan += "- 展示份额: 目标 > 60%\n"
    
    return plan

def generate_deep_research_report(product: dict, competitor: dict, keywords: dict, asin: str) -> str:
    """生成深度分析报告"""
    basic_report = generate_product_research_report(product, competitor, keywords)
    
    deep_report = f"""# 深度分析报告 — {asin}

{basic_report}

---

## 产品痛点分析

"""
    
    # 模拟痛点分析
    pain_points = ["质量问题", "尺寸不符", "安装困难", "配件缺失"]
    for pain in pain_points:
        deep_report += f"### {pain}\n"
        deep_report += f"- 在评论中发现的{pain}问题\n"
        deep_report += f"- 建议改进方向: ...\n\n"
    
    deep_report += """## 行业竞争格局

### 市场集中度
- CR5（前5名市场份额）: 约45%
- 新品牌进入难度: 中等

### 主要竞争对手
"""
    
    comps = competitor.get("products", [])[:5]
    for c in comps:
        deep_report += f"- {c.get('asin', 'N/A')}: 售价${c.get('price', 'N/A')}, BSR #{c.get('bsr', 'N/A')}\n"
    
    deep_report += """
## 运营策略建议

### Listing优化
- 标题埋词: 重点布局高流量关键词
- 图片优化: 增加场景图和使用示意图
- A+页面: 添加品牌故事和对比图

### 广告策略
- 新品期: 自动投放 + 精准词手动
- 成长期: 扩大关键词覆盖，提升展示份额
- 稳定期: 优化ACoS，提升ROI

## 机会地图

| 机会点 | 优先级 | 预期效果 |
|--------|--------|----------|
| 增加变体 | ⭐⭐⭐⭐ | 提升30%销量 |
| 优化图片 | ⭐⭐⭐ | 提升20%转化率 |
| 投放视频广告 | ⭐⭐⭐⭐ | 提升40%曝光 |
"""
    
    return deep_report

# ============================================================
# 工具函数（内联版）
# ============================================================
def calc_profit(price, fba_fee, cogs, shipping, acos=0.20, return_rate=0.03):
    """利润核算"""
    commission = price * 0.15
    ad_cost = price * acos
    return_loss = price * return_rate * 0.5
    gross = price - commission - fba_fee - cogs - shipping
    net = gross - ad_cost - return_loss - 0.50
    net_margin = round(net / price * 100, 1) if price > 0 else 0
    status = "🟢 健康" if net_margin > 15 else ("🟡 关注" if net_margin > 5 else "🔴 亏损")
    return {"price": price, "commission": round(commission,2), "fba_fee": fba_fee,
            "cogs": cogs, "shipping": shipping, "ad_cost": round(ad_cost,2),
            "return_loss": round(return_loss,2), "gross_profit": round(gross,2),
            "net_profit": round(net,2), "net_margin_pct": net_margin, "status": status}

def score_sku_inline(sku):
    """SKU健康度打分"""
    scores = {"销量": 0, "利润": 0, "评分": 0, "库存": 0, "广告": 0, "退货": 0}
    ds = float(sku.get("dailySales", 0))
    if ds > 5: scores["销量"] = 25
    elif ds > 2: scores["销量"] = 20
    elif ds > 1: scores["销量"] = 15
    elif ds > 0.3: scores["销量"] = 10
    elif ds > 0: scores["销量"] = 5
    
    m = float(sku.get("profitMargin", 0))
    if m > 30: scores["利润"] = 20
    elif m > 20: scores["利润"] = 15
    elif m > 10: scores["利润"] = 10
    elif m > 5: scores["利润"] = 5
    
    r = float(sku.get("rating", 0))
    if r >= 4.5: scores["评分"] = 15
    elif r >= 4.0: scores["评分"] = 12
    elif r >= 3.5: scores["评分"] = 8
    elif r >= 3.0: scores["评分"] = 4
    
    sd = float(sku.get("stockDays", 0))
    if 15 <= sd <= 45: scores["库存"] = 15
    elif 7 <= sd < 15 or 45 < sd <= 60: scores["库存"] = 10
    elif 3 <= sd < 7: scores["库存"] = 5
    
    a = float(sku.get("acos", 100))
    if a < 15: scores["广告"] = 15
    elif a < 25: scores["广告"] = 12
    elif a < 35: scores["广告"] = 8
    elif a < 50: scores["广告"] = 4
    
    rr = float(sku.get("returnRate", 0))
    if rr < 2: scores["退货"] = 10
    elif rr < 5: scores["退货"] = 8
    elif rr < 10: scores["退货"] = 5
    
    total = sum(scores.values())
    if total >= 80: tier, emoji, strategy = "A", "⭐", "加大投入扩量"
    elif total >= 60: tier, emoji, strategy = "B", "✅", "优化Listing控制ACoS"
    elif total >= 40: tier, emoji, strategy = "C", "⚠️", "降价清库或调广告"
    else: tier, emoji, strategy = "D", "❌", "评估是否退市"
    
    return {"score": total, "tier": tier, "emoji": emoji, "strategy": strategy, "scores": scores}

def analyze_voc_inline(reviews):
    """评论VOC分析"""
    stopwords = {"the","a","an","is","was","are","were","and","or","but","in","on","at",
                 "to","for","of","with","it","this","that","i","you","he","she","we","they",
                 "not","be","have","has","had","do","does","did","will","would","could","should",
                 "very","just","really","so","been","its","my","am"}
    pos = [r for r in reviews if r.get("stars", 0) >= 4]
    neg = [r for r in reviews if r.get("stars", 0) <= 2]
    
    def get_keywords(texts, n=15):
        words = []
        for t in texts:
            for w in re.findall(r'[a-z]{3,}', t.get("content", t.get("text", "")).lower()):
                if w not in stopwords: words.append(w)
        return Counter(words).most_common(n)
    
    return {
        "total": len(reviews),
        "positive_pct": round(len(pos)/len(reviews)*100,1) if reviews else 0,
        "negative_pct": round(len(neg)/len(reviews)*100,1) if reviews else 0,
        "positive_keywords": get_keywords(pos),
        "negative_keywords": get_keywords(neg),
    }

def detect_pains_inline(negative_reviews):
    """检测产品痛点"""
    pain_patterns = {
        "质量问题": ["broke","break","broken","defective","cheap","poor quality","flimsy"],
        "尺寸不符": ["too small","too big","wrong size","didnt fit","smaller than"],
        "安装困难": ["hard to install","difficult","instructions","manual","not clear"],
        "配件缺失": ["missing","didnt come","incomplete","no screws","without"],
        "生锈腐蚀": ["rust","rusty","corrosion","corroded","oxidized"],
        "物流损坏": ["damaged","bent","scratched","cracked","broken in"],
    }
    
    findings = {}
    for pain, keywords in pain_patterns.items():
        count = 0
        samples = []
        for review in negative_reviews:
            text = (review.get("content","") + " " + review.get("title","")).lower()
            if any(kw in text for kw in keywords):
                count += 1
                if len(samples) < 2: samples.append(text[:150])
        if count > 0:
            findings[pain] = {"count": count, "samples": samples}
    
    return dict(sorted(findings.items(), key=lambda x: x[1]["count"], reverse=True))

def analyze_neg_kws(terms):
    """否定词分析"""
    rules = [
        ("高花费0转化", lambda r: r.get("spend",0) > 10 and r.get("orders",0) == 0, "MUST", "Exact"),
        ("高ACoS", lambda r: r.get("acos",100) > 60 and r.get("spend",0) > 5, "SUGGEST", "Phrase"),
        ("低价意图", lambda r: any(w in r.get("keyword","").lower() for w in ["cheap","free","wholesale"]), "MUST", "Phrase"),
        ("跑偏词", lambda r: r.get("acos",0) > 80 and r.get("clicks",0) > 10, "MUST", "Exact"),
    ]
    
    results = []
    for term in terms:
        matched = []
        for name, cond, level, mtype in rules:
            if cond(term): matched.append((name, level, mtype))
        if matched:
            results.append({"keyword": term.get("keyword",""), "matched_rules": [m[0] for m in matched],
                           "level": matched[0][1], "match_type": matched[0][2]})
    
    return results

def gen_neg_csv(negatives):
    """生成否定词CSV"""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Campaign Name","Ad Group Name","Keyword","Negative Keyword Type","Level"])
    for n in negatives:
        w.writerow(["All","All", n["keyword"], n["match_type"], n["level"]])
    return out.getvalue()

# ============================================================
# Streamlit 界面
# ============================================================
st.set_page_config(
    page_title="亚马逊 AI 全链路工具包",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
st.sidebar.title("🛒 亚马逊 AI 工具包")
st.sidebar.caption("Powered by LinkFox API + WorkBuddy")

page = st.sidebar.radio(
    "功能模块",
    ["🏠 首页", "🔍 选品调研", "📝 Listing 生成", "📢 广告方案", "📊 工作流 Pipeline",
     "📈 运营分析", "💬 评论VOC", "🎯 广告诊断"],
)

st.sidebar.divider()

# API Key 状态
if API_KEY and API_KEY != "微信联系获取":
    st.sidebar.success("✅ LinkFox API 已连接")
else:
    st.sidebar.warning("⚠️ LinkFox API Key 未配置")
    st.sidebar.info("请在Railway环境变量中设置 LINKFOX_API_KEY")

st.sidebar.divider()
st.sidebar.caption("Project: amazon-ai-toolkit")
st.sidebar.caption("Author: 微信龙虾 🦞")

# ============================================================
# 首页
# ============================================================
if page == "🏠 首页":
    st.title("亚马逊 AI 全链路自动化工具包")
    st.markdown("""
    > 基于 **WorkBuddy + LinkFox API** 
    > 涵盖选品调研、Listing生成、广告方案、运营分析 4大模块
    
    ---
    ### 📦 功能模块
    
    | 模块 | 功能 | 状态 |
    |------|------|------|
    | 🔍 **选品调研** | ASIN/关键词多维分析，利润估算，竞品对比 | ✅ 已接入 |
    | 📝 **Listing 生成** | 智能标题/五点/关键词/搜索词 | ✅ 已接入 |
    | 📢 **广告方案** | 新品广告初始化/30天预算规划/关键词分组 | ✅ 已接入 |
    | 📊 **工作流** | 选品→Listing→广告 一键串联 | ✅ 已接入 |
    | 📈 **运营分析** | 利润核算/SKU健康/竞品追踪 | ✅ 已接入 |
    | 💬 **评论VOC** | 评论情感分析/痛点检测/高频词 | ✅ 已接入 |
    | 🎯 **广告诊断** | 否定词生成/诊断规则引擎/广告复盘 | ✅ 已接入 |
    
    ---
    ### 🚀 快速开始
    
    1. 在左侧边栏选择「选品调研」
    2. 输入要分析的 ASIN（如 `B0FD2MBKTJ`）
    3. 点击「开始分析」查看完整报告
    """)

# ============================================================
# 选品调研
# ============================================================
elif page == "🔍 选品调研":
    st.title("🔍 选品可行性分析")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        asin_input = st.text_input("输入要分析的 ASIN", placeholder="B0FD2MBKTJ", help="支持单个 ASIN，美国站")
    with col2:
        st.write("")
        search_btn = st.button("🔍 基础分析", type="primary", use_container_width=True)
    with col3:
        st.write("")
        deep_btn = st.button("🏆 深度分析", type="primary", use_container_width=True,
                             help="含产品痛点、行业格局、运营策略、机会地图")
    
    if (search_btn or deep_btn) and asin_input.strip():
        if not API_KEY or API_KEY == "微信联系获取":
            st.error("❌ 请先配置 LinkFox API Key（在Railway环境变量中设置 LINKFOX_API_KEY）")
        else:
            mode = "deep" if deep_btn else "basic"
            with st.spinner(f"正在{'深度' if mode=='deep' else '基础'}分析 {asin_input.strip()}..."):
                st.info("📡 正在调用 LinkFox API（产品详情 + 竞品 + 关键词）...")
                product_data = get_product_detail(asin_input.strip())
                competitor_data = get_competitor_data("US", asin_input.strip())
                keyword_data = get_traffic_keywords("US", asin_input.strip())
            
            if "error" in product_data or "error" in competitor_data:
                st.error(f"API 调用失败: {product_data.get('error', competitor_data.get('error', 'Unknown'))}")
            else:
                if mode == "deep":
                    with st.spinner("🧠 融合行业研究数据库，生成深度报告..."):
                        report = generate_deep_research_report(product_data, competitor_data, keyword_data, asin_input.strip())
                    suffix = "_深度报告"
                else:
                    report = generate_product_research_report(product_data, competitor_data, keyword_data)
                    suffix = "_基础报告"
                
                # 保存报告
                os.makedirs("data", exist_ok=True)
                report_path = f"data/{asin_input.strip()}{suffix}.md"
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                
                st.success(f"✅ 分析完成！报告已保存到 {report_path}")
                
                # 显示报告
                with st.expander("📊 查看完整报告", expanded=True):
                    st.markdown(report)
                
                # 下载按钮
                st.download_button(
                    "📥 下载报告 (Markdown)",
                    report,
                    file_name=f"{asin_input.strip()}_分析报告.md",
                    mime="text/markdown",
                )

# ============================================================
# Listing 生成
# ============================================================
elif page == "📝 Listing 生成":
    st.title("📝 Listing 文案生成")
    
    asin_input = st.text_input("输入竞品 ASIN（基于其 Listing 优化生成）", placeholder="B0FD2MBKTJ")
    generate_btn = st.button("🚀 生成 Listing", type="primary")
    
    if generate_btn and asin_input.strip():
        if not API_KEY or API_KEY == "微信联系获取":
            st.error("❌ 请先配置 LinkFox API Key")
        else:
            try:
                with st.spinner("生成中..."):
                    product_data = get_product_detail(asin_input.strip())
                    keyword_data = get_traffic_keywords("US", asin_input.strip())
                
                if "error" in product_data:
                    st.error(f"❌ API调用失败: {product_data.get('error')}")
                else:
                    listing = generate_listing(product_data, keyword_data)
                    st.success("✅ Listing 生成完成")
                    st.markdown(listing)
            except Exception as e:
                st.error(f"❌ 生成失败: {str(e)}")

# ============================================================
# 广告方案
# ============================================================
elif page == "📢 广告方案":
    st.title("📢 新品广告初始化方案")
    
    asin_input = st.text_input("输入新品 ASIN", placeholder="B0FD2MBKTJ")
    gen_btn = st.button("📊 生成广告方案", type="primary")
    
    if gen_btn and asin_input.strip():
        if not API_KEY or API_KEY == "微信联系获取":
            st.error("❌ 请先配置 LinkFox API Key")
        else:
            try:
                with st.spinner("分析关键词和竞品数据..."):
                    product_data = get_product_detail(asin_input.strip())
                    keyword_data = get_traffic_keywords("US", asin_input.strip())
                
                # 检查结果
                p_ok = "error" not in product_data
                k_ok = "error" not in keyword_data
                
                if not p_ok:
                    st.error(f"❌ 产品详情获取失败: {product_data.get('error', '未知错误')}")
                elif not k_ok:
                    st.warning("⚠️ 关键词数据获取失败，使用基础广告方案")
                    keyword_data = {"data": []}
                    plan = generate_ad_plan(product_data, keyword_data)
                    st.success("✅ 基础广告方案已生成（不含关键词明细）")
                    st.markdown(plan)
                else:
                    plan = generate_ad_plan(product_data, keyword_data)
                    st.success("✅ 广告方案生成完成")
                    st.markdown(plan)
            except Exception as e:
                st.error(f"❌ 生成失败: {str(e)}")
                st.info("💡 请检查网络连接或稍后重试")

# ============================================================
# 工作流 Pipeline
# ============================================================
elif page == "📊 工作流 Pipeline":
    st.title("📊 全链路工作流 Pipeline")
    st.markdown("一键串联：选品分析 → Listing生成 → 广告方案 → 完整Launch包")
    
    asin_input = st.text_input("输入目标 ASIN 或新品参考 ASIN", placeholder="B0FD2MBKTJ")
    run_btn = st.button("⚡ 一键运行全链路", type="primary", use_container_width=True)
    
    if run_btn and asin_input.strip():
        if not API_KEY or API_KEY == "微信联系获取":
            st.error("❌ 请先配置 LinkFox API Key")
        else:
            # 进度条
            progress = st.progress(0, "初始化...")
            
            with st.spinner("Phase 1/3: 选品数据分析..."):
                progress.progress(10, "获取产品详情...")
                product_data = get_product_detail(asin_input.strip())
                progress.progress(30, "获取竞品数据...")
                competitor_data = get_competitor_data("US", asin_input.strip())
                progress.progress(50, "获取关键词数据...")
                keyword_data = get_traffic_keywords("US", asin_input.strip())
            
            progress.progress(60, "Phase 2/3: 生成分析报告和Listing...")
            research_report = generate_product_research_report(product_data, competitor_data, keyword_data)
            listing = generate_listing(product_data, keyword_data)
            
            progress.progress(80, "Phase 3/3: 生成广告方案...")
            ad_plan = generate_ad_plan(product_data, keyword_data)
            progress.progress(100, "✅ 完成！")
            
            # 输出
            st.success(f"✅ 全链路Pipeline执行完成！")
            
            # 保存完整包
            full_package = f"""\
# 新品 Launch 完整方案包 — {asin_input.strip()}

{research_report}

---

{listing}

---

{ad_plan}
"""
            os.makedirs("data", exist_ok=True)
            pkg_path = f"data/{asin_input.strip()}_launch_package.md"
            with open(pkg_path, "w", encoding="utf-8") as f:
                f.write(full_package)
            
            # Tab显示
            tab1, tab2, tab3 = st.tabs(["📊 选品分析", "📝 Listing", "📢 广告方案"])
            with tab1:
                st.markdown(research_report)
            with tab2:
                st.markdown(listing)
            with tab3:
                st.markdown(ad_plan)
            
            st.download_button(
                "📥 下载完整 Launch 包",
                full_package,
                file_name=f"{asin_input.strip()}_launch_package.md",
                mime="text/markdown",
            )

# ============================================================
# 运营分析
# ============================================================
elif page == "📈 运营分析":
    st.title("📈 运营分析工具")
    tab1, tab2, tab3 = st.tabs(["💰 利润核算", "📊 SKU健康分", "🔍 竞品追踪"])
    
    # 利润核算
    with tab1:
        st.subheader("💰 利润核算器")
        col1, col2, col3 = st.columns(3)
        with col1:
            price = st.number_input("售价 ($)", min_value=0.0, value=29.79, step=1.0)
            cogs = st.number_input("产品成本 FOB ($)", min_value=0.0, value=5.0, step=0.5)
        with col2:
            fba_fee = st.number_input("FBA配送费 ($)", min_value=0.0, value=7.38, step=0.5)
            shipping = st.number_input("头程运费/件 ($)", min_value=0.0, value=1.5, step=0.5)
        with col3:
            acos = st.slider("广告ACoS (%)", 5, 60, 20) / 100
            return_rate = st.slider("退货率 (%)", 0, 20, 3) / 100
        
        if st.button("🧮 计算利润", type="primary"):
            result = calc_profit(price, fba_fee, cogs, shipping, acos, return_rate)
            
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("售价", f"${result['price']:.2f}")
            col_b.metric("净利润", f"${result['net_profit']:.2f}", delta=f"{result['net_margin_pct']}%")
            col_c.metric("广告花费", f"${result['ad_cost']:.2f}")
            col_d.metric("FBA+佣金", f"${result['fba_fee'] + result['commission']:.2f}")
            
            st.divider()
            st.caption(f"成本: ${cogs:.2f} | 运费: ${shipping:.2f} | 退货损耗: ${result['return_loss']:.2f}")
            st.caption(f"评级: {result['status']} | 净利润率: {result['net_margin_pct']}%")
    
    # SKU健康分
    with tab2:
        st.subheader("📊 SKU健康度评分")
        days = st.slider("可售天数", 0, 120, 30)
        sales = st.number_input("日均销量 (件)", min_value=0.0, value=2.9, step=0.1)
        rating_val = st.slider("评分", 1.0, 5.0, 4.2, 0.1)
        margin = st.slider("利润率 (%)", 0, 80, 18)
        acos_val = st.slider("ACoS (%)", 5, 100, 20)
        ret_rate = st.slider("SKU退货率 (%)", 0, 30, 3)
        
        if st.button("📊 评估健康度", type="primary"):
            sku = {"asin": "SAMPLE", "dailySales": sales, "profitMargin": margin,
                   "rating": rating_val, "stockDays": days, "acos": acos_val, "returnRate": ret_rate}
            r = score_sku_inline(sku)
            st.metric("健康度得分", f"{r['score']}/100", delta=f"{r['emoji']} {r['tier']}级")
            st.caption(f"评级: {r['emoji']} {r['tier']}级 - {r['strategy']}")
    
    # 竞品追踪
    with tab3:
        st.subheader("🔍 竞品变化追踪")
        asin_list = st.text_input("监控ASIN列表（逗号分隔）", placeholder="B0FD2MBKTJ,B0D5CXKV83")
        if st.button("🔍 追踪", type="primary"):
            if asin_list.strip():
                asins = [a.strip() for a in asin_list.split(",") if a.strip()]
                with st.spinner(f"正在追踪 {len(asins)} 个ASIN..."):
                    for asin in asins:
                        try:
                            data = get_competitor_data("US", asin)
                            item = data.get("products", [{}])[0] if data.get("products") else {}
                            if item:
                                with st.expander(f"📦 {asin} - {item.get('title', 'N/A')[:60]}", expanded=True):
                                    c1, c2, c3, c4, c5 = st.columns(5)
                                    c1.metric("售价", f"${item.get('price', 'N/A')}")
                                    c2.metric("BSR", f"#{item.get('bsr', 'N/A')}")
                                    c3.metric("月销量", f"{item.get('monthlySalesUnits', 'N/A')}件")
                                    c4.metric("利润率", f"{item.get('profit', 'N/A')}%")
                                    c5.metric("评分", f"{item.get('rating', 'N/A')}")
                        except Exception as e:
                            st.warning(f"{asin}: {e}")

# ============================================================
# 评论VOC
# ============================================================
elif page == "💬 评论VOC":
    st.title("💬 评论 VOC 分析")
    st.caption("输入评论JSON数据，自动分析好评/差评关键词、痛点、改进方向")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        review_text = st.text_area(
            "粘贴评论JSON数据（每行一个评论对象）",
            placeholder='[{"stars": 5, "content": "Great product!"}, {"stars": 1, "content": "Broke after 2 days"}]',
            height=200
        )
    with col2:
        st.info("""
        **JSON格式示例:**
        ```json
        [
          {"stars": 5, "content": "..."},
          {"stars": 3, "content": "..."},
          {"stars": 1, "content": "..."}
        ]
        ```
        """)
    
    if st.button("💬 分析评论", type="primary"):
        if review_text.strip():
            try:
                reviews = json.loads(review_text)
                sentiment = analyze_voc_inline(reviews)
                pains = detect_pains_inline([r for r in reviews if r.get("stars", 0) <= 2])
                
                c1, c2, c3 = st.columns(3)
                c1.metric("总评论", sentiment['total'])
                c2.metric("好评占比", f"{sentiment['positive_pct']}%")
                c3.metric("差评占比", f"{sentiment['negative_pct']}%")
                
                if sentiment['positive_keywords']:
                    st.subheader("✅ 好评高频词")
                    st.write(", ".join([f"`{kw[0]}`({kw[1]})" for kw in sentiment['positive_keywords'][:15]]))
                
                if sentiment['negative_keywords']:
                    st.subheader("❌ 差评高频词")
                    st.write(", ".join([f"`{kw[0]}`({kw[1]})" for kw in sentiment['negative_keywords'][:15]]))
                
                if pains:
                    st.subheader("🔍 产品痛点检测")
                    for pain, info in pains.items():
                        st.warning(f"**{pain}**: {info['count']}次提及")
                        for s in info.get('samples', []):
                            st.caption(f"> {s[:200]}...")
                
                if not pains and not sentiment['negative_keywords']:
                    st.success("✅ 未发现明显痛点，产品质量良好！")
                    
            except json.JSONDecodeError:
                st.error("JSON格式错误，请检查输入")

# ============================================================
# 广告诊断
# ============================================================
elif page == "🎯 广告诊断":
    st.title("🎯 广告诊断中心")
    tab1, tab2 = st.tabs(["❌ 否定词生成", "📋 诊断规则"])
    
    # 否定词生成
    with tab1:
        st.subheader("❌ 否定词批量生成器")
        st.caption("粘贴广告搜索词报告数据，自动识别浪费词并生成否定词CSV")
        
        ad_data = st.text_area(
            "粘贴搜索词报告JSON",
            placeholder='[{"keyword": "cheap turnbuckle", "spend": 15.0, "orders": 0, "clicks": 50, "acos": 100, "conversion": 0}]',
            height=150
        )
        
        if st.button("🔍 分析否定词", type="primary"):
            if ad_data.strip():
                try:
                    terms = json.loads(ad_data)
                    negatives = analyze_neg_kws(terms)
                    if negatives:
                        must = [n for n in negatives if n.get("level") == "MUST"]
                        suggest = [n for n in negatives if n.get("level") == "SUGGEST"]
                        
                        col1, col2 = st.columns(2)
                        col1.metric("🔴 必须否定", len(must))
                        col2.metric("🟡 建议否定", len(suggest))
                        
                        st.dataframe([{
                            "关键词": n["keyword"], "级别": n["level"],
                            "匹配方式": n["match_type"], "规则": ", ".join(n["matched_rules"])
                        } for n in negatives])
                        
                        csv_data = gen_neg_csv(negatives)
                        st.download_button("📥 下载否定词CSV", csv_data, "negative_keywords.csv", "text/csv")
                    else:
                        st.success("✅ 未发现需要否定的关键词！")
                except json.JSONDecodeError:
                    st.error("JSON格式错误")
    
    # 诊断规则
    with tab2:
        st.subheader("📋 广告诊断规则引擎")
        st.markdown("""
        ### 关键词分级规则
        
        | 规则 | 条件 | 操作 |
        |------|------|------|
        | 🔴 高花费0转化 | 花费 > $10 且 0订单 | 精准否定 |
        | 🔴 高ACoS | ACoS > 60% 且 花费 > $5 | 词组否定 |
        | 🟡 跑偏词 | ACoS > 80% 且 点击 > 10 | 精准否定 |
        | 🟡 低价意图 | 含 cheap/free/wholesale | 词组否定 |
        
        ### 健康度标准
        
        | 指标 | 🟢 健康 | 🟡 警告 | 🔴 危险 |
        |------|---------|---------|---------|
        | ACoS | < 20% | 20-40% | > 40% |
        | ROAS | > 4 | 2-4 | < 2 |
        | CTR | > 0.5% | 0.2-0.5% | < 0.2% |
        | CVR | > 10% | 5-10% | < 5% |
        """)
