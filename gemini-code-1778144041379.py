import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 页面基本配置
st.set_page_config(page_title="BioGemini Pro - 智能文献调研站", page_icon="🧬", layout="wide")

# 2. 自定义 CSS：适配深浅模式，解决全宽显示问题
st.markdown("""
    <style>
    /* 全局背景微调 */
    .stApp { background-color: transparent; }
    
    /* 按钮样式优化 */
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
        padding: 24px; 
        border-radius: 12px; 
        background-color: rgba(128, 128, 128, 0.05); 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        margin-bottom: 20px; 
    }
    
    .paper-title { font-size: 1.3rem; font-weight: 600; margin-bottom: 10px; line-height: 1.4; }
    
    .year-tag { 
        background-color: #4A90E2; 
        color: white; 
        padding: 2px 10px; 
        border-radius: 4px; 
        font-size: 0.85rem; 
        font-weight: bold; 
        margin-right: 10px;
    }

    /* AI 分析框样式 - 核心改进点 */
    .ai-box {
        background-color: rgba(74, 144, 226, 0.1); /* 半透明蓝色，适配深浅模式 */
        padding: 25px; 
        border-left: 6px solid #4A90E2; 
        border-radius: 8px;
        margin-top: 15px;
        margin-bottom: 25px;
        width: 100%; /* 强制全宽显示 */
        line-height: 1.7;
        font-size: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 配置 Gemini 模型
api_key = st.secrets.get("GEMINI_API_KEY")
model = None

@st.cache_resource
def load_model(key):
    if not key: return None
    genai.configure(api_key=key)
    try:
        # 尝试使用 1.5-flash，这在大部分 API Key 中最稳
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        try:
            # 备选逻辑：获取第一个可用模型
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            return genai.GenerativeModel(available[0]) if available else None
        except:
            return None

model = load_model(api_key)

# 4. PubMed 核心逻辑
def search_pubmed_advanced(query, years=5, max_results=10, sort="relevance"):
    current_year = datetime.now().year
    min_year = current_year - years
    advanced_query = f"({query}) AND ({min_year}:{current_year}[DP])"
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": advanced_query, "retmax": max_results, "retmode": "json", "sort": sort}
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
        year = pub_year.text if pub_year is not None else "Recent"
        return title, abstract_text, year
    except:
        return None, None, None

# 5. 界面布局
with st.sidebar:
    st.markdown("### 🧬 检索控制台")
    if model:
        st.success("✅ AI 模型已就绪")
    else:
        st.error("❌ 模型未连接，请检查 API Key")
    
    search_years = st.slider("时间跨度 (近 X 年)", 1, 20, 5)
    search_sort = st.selectbox("排序规则", ["relevance", "pub_date"], format_func=lambda x: "相关性优先" if x=="relevance" else "最新日期优先")
    max_num = st.number_input("展示条数", 5, 50, 10)

st.title("🔬 BioGemini Pro")
st.markdown("##### 结合 PubMed 实时检索与 Gemini 1.5 深度分析的学术助手")

user_query = st.text_input("", placeholder="输入你的研究领域或关键词 (例如: RSV vaccine)...", label_visibility="collapsed")

if user_query:
    with st.spinner("🔍 正在检索 PubMed 数据库..."):
        ids = search_pubmed_advanced(user_query, years=search_years, max_results=max_num, sort=search_sort)
    
    if not ids:
        st.warning("未能检索到相关结果。")
    else:
        st.success(f"已为您精选 {len(ids)} 篇文献")
        for pmid in ids:
            title, abstract, year = get_details(pmid)
            if not title: continue
            
            # --- 论文卡片展示 ---
            st.markdown(f"""
            <div class="paper-card">
                <span class="year-tag">{year}</span>
                <span style="opacity: 0.7; font-size: 0.85rem;">PMID: {pmid}</span>
                <div class="paper-title">{title}</div>
                <div style="margin-top: 10px;">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #4A90E2;">🔗 查看原文 (PubMed)</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- 分析按钮与全宽结果展示 ---
            # 按钮放在一列里防止太长
            btn_col, _ = st.columns([1.5, 5])
            with btn_col:
                analyze_btn = st.button("✨ 深度分析摘要", key=f"ai_{pmid}")
            
            if analyze_btn:
                if not model:
                    st.error("模型未初始化，请检查 Secrets 配置。")
                else:
                    with st.spinner("Gemini 正在分析中..."):
                        prompt = f"你是一位资深生物医学专家。请针对以下摘要进行深度分析并用中文回答，需包含：1.【中文标题翻译】 2.【核心结论总结】 3.【研究亮点与局限】。内容如下：{abstract}"
                        try:
                            response = model.generate_content(prompt)
                            # 渲染 AI 分析结果，脱离 Column 限制，全宽显示
                            st.markdown(f'<div class="ai-box">{response.text}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"分析失败: {e}")
            
            st.markdown("<hr style='opacity: 0.1; margin: 20px 0;'>", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2024 BioGemini | 助力学术调研与文献理解")
