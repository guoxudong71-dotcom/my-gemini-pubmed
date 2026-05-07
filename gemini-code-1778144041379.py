import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 页面基本配置：使用宽屏模式
st.set_page_config(page_title="BioGemini Pro - 智能文献调研站", page_icon="🧬", layout="wide")

# 2. 自定义 CSS：打造 Notion 风格的学术卡片
st.markdown("""
    <style>
    /* 全局背景与字体 */
    .main { background-color: #fcfcfc; }
    
    /* 自定义按钮样式 */
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        border: 1px solid #4A90E2; 
        color: #4A90E2; 
        background-color: transparent;
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background-color: #4A90E2; 
        color: white; 
    }

    /* 论文卡片容器 */
    .paper-card { 
        padding: 20px; 
        border-radius: 12px; 
        background-color: white; 
        border: 1px solid #eaeaea; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    
    /* 标题样式 */
    .paper-title { color: #1a1a1a; font-size: 1.2rem; font-weight: 600; margin-bottom: 8px; }
    
    /* 标签样式 */
    .year-tag { 
        background-color: #e1f0ff; 
        color: #007bff; 
        padding: 2px 8px; 
        border-radius: 4px; 
        font-size: 0.85rem; 
        font-weight: bold; 
        margin-right: 10px;
    }

    /* AI 分析框样式 */
    .ai-box {
        background-color: #f0f7ff; 
        padding: 18px; 
        border-left: 5px solid #4A90E2; 
        border-radius: 8px;
        margin-top: 10px;
        font-family: sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 配置 Gemini 模型（自动侦测可用版本）
try:
    genai.configure(api_key=api_key)
    
    # 自动获取当前 API Key 支持的所有模型
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # 优先选择 Flash 模型（速度快且免费额度多），如果找不到则选第一个可用的
    selected_model = next((m for m in available_models if 'gemini-1.5-flash' in m), None)
    if not selected_model:
        selected_model = available_models[0] if available_models else "models/gemini-1.5-flash"
    
    model = genai.GenerativeModel(selected_model)
    st.sidebar.success(f"✅ 已自动连接模型: {selected_model}")
except Exception as e:
    st.error(f"❌ Gemini 配置失败: {e}")
    
# 4. PubMed 核心逻辑：高级检索与数据提取
def search_pubmed_advanced(query, years=5, max_results=10, sort="relevance"):
    current_year = datetime.now().year
    min_year = current_year - years
    # 构造高级检索词：组合年份过滤
    advanced_query = f"({query}) AND ({min_year}:{current_year}[DP])"
    
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": advanced_query,
        "retmax": max_results,
        "retmode": "json",
        "sort": sort
    }
    try:
        r = requests.get(search_url, params=params, timeout=10)
        return r.json().get("esearchresult", {}).get("idlist", [])
    except:
        return []

def get_details(pmid):
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    try:
        r = requests.get(fetch_url, timeout=10)
        root = ET.fromstring(r.content)
        title = root.find(".//ArticleTitle").text if root.find(".//ArticleTitle") is not None else "Untitled"
        abstracts = root.findall(".//AbstractText")
        abstract_text = " ".join([n.text for n in abstracts if n.text])
        pub_year = root.find(".//PubDate/Year")
        year = pub_year.text if pub_year is not None else "近期"
        return title, abstract_text, year
    except:
        return None, None, None

# --- 5. 界面布局 ---

# 侧边栏：检索控制台
with st.sidebar:
    st.markdown("### 🧬 检索控制台")
    search_years = st.slider("时间跨度 (近 X 年)", 1, 20, 5)
    search_sort = st.selectbox("排序规则", ["relevance", "pub_date"], format_func=lambda x: "相关性优先" if x=="relevance" else "最新日期优先")
    max_num = st.number_input("展示条数", 5, 50, 10)
    st.markdown("---")
    st.caption("系统状态: 🟢 Gemini API 已连接")

# 主界面标题
st.title("🔬 BioGemini Pro")
st.markdown("##### 结合 PubMed 实时检索与 Gemini 1.5 深度分析的学术助手")

# 搜索交互
col_input, col_btn = st.columns([6, 1])
with col_input:
    user_query = st.text_input("", placeholder="输入你的研究领域或关键词...", label_visibility="collapsed")
with col_btn:
    search_trigger = st.button("检索")

if user_query or search_trigger:
    with st.spinner("🔍 正在扫描 PubMed 并构建知识索引..."):
        ids = search_pubmed_advanced(user_query, years=search_years, max_results=max_num, sort=search_sort)
    
    if not ids:
        st.warning("未能检索到相关结果。建议尝试缩短检索词，或在侧边栏增加年份范围。")
    else:
        st.success(f"已为您精选 {len(ids)} 篇最近 {search_years} 年内的核心文献")
        
        for pmid in ids:
            title, abstract, year = get_details(pmid)
            if not title: continue
            
            # 使用自定义卡片渲染
            st.markdown(f"""
            <div class="paper-card">
                <span class="year-tag">{year}</span>
                <span style="color: #666; font-size: 0.8rem;">PMID: {pmid}</span>
                <div class="paper-title">{title}</div>
                <div style="margin-top: 10px;">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #4A90E2; font-size: 0.85rem;">🔗 查看原文 (PubMed)</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 交互按钮
            btn_col, _ = st.columns([1, 3])
            with btn_col:
                if st.button("✨ AI 深度分析", key=f"ai_{pmid}"):
                    with st.spinner("AI 正在研读摘要并提取 Insight..."):
                        prompt = f"""
                        作为学术专家，请分析此摘要并用中文输出：
                        1.【中文标题】：准确翻译。
                        2.【核心结论】：用一句话总结研究解决了什么问题。
                        3.【专属 Insight】：此研究对同行有何具体启发或其潜在局限。
                        内容如下：{abstract}
                        """
                        try:
                            response = model.generate_content(prompt)
                            st.markdown(f"""
                            <div class="ai-box">
                                {response.text}
                            </div>
                            """, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"分析失败: {e}")
            st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2024 BioGemini | 提升科研效率的智能底座")
