import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 页面基本配置
st.set_page_config(page_title="BioGemini Pro - 智能文献调研站", page_icon="🧬", layout="wide")

# 2. 自定义 CSS
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stButton>button { width: 100%; border-radius: 8px; border: 1px solid #4A90E2; color: #4A90E2; background-color: transparent; transition: 0.3s; }
    .stButton>button:hover { background-color: #4A90E2; color: white; }
    .paper-card { padding: 20px; border-radius: 12px; background-color: white; border: 1px solid #eaeaea; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .paper-title { color: #1a1a1a; font-size: 1.2rem; font-weight: 600; margin-bottom: 8px; }
    .year-tag { background-color: #e1f0ff; color: #007bff; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-right: 10px; }
    /* AI 分析框样式 - 优化版 */
    .ai-box {
        background-color: rgba(74, 144, 226, 0.1); /* 使用透明度，适配深浅模式 */
        padding: 20px; 
        border-left: 5px solid #4A90E2; 
        border-radius: 8px;
        margin-top: 15px;
        margin-bottom: 15px;
        width: 100%; /* 解决竖条问题，强制全宽 */
        line-height: 1.6;
        color: inherit; /* 文字颜色继承系统，深色模式变白，浅色模式变黑 */
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 配置 Gemini 模型
# --- 修正点：先获取 Key，再预定义 model ---
api_key = st.secrets.get("GEMINI_API_KEY")
model = None

if not api_key:
    st.error("🔑 未在 Secrets 中找到 GEMINI_API_KEY，请检查配置。")
else:
    try:
        genai.configure(api_key=api_key)
        # 获取可用模型列表
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = next((m for m in available_models if 'gemini-1.5-flash' in m), None)
        if not selected_model:
            selected_model = available_models[0] if available_models else "models/gemini-1.5-flash"
        
        model = genai.GenerativeModel(selected_model)
        st.sidebar.success(f"✅ 已连接: {selected_model}")
    except Exception as e:
        st.sidebar.error(f"❌ 模型初始化失败: {e}")

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
        year = pub_year.text if pub_year is not None else "近期"
        return title, abstract_text, year
    except:
        return None, None, None

# 5. 界面布局
with st.sidebar:
    st.markdown("### 🧬 检索控制台")
    search_years = st.slider("时间跨度 (近 X 年)", 1, 20, 5)
    search_sort = st.selectbox("排序规则", ["relevance", "pub_date"], format_func=lambda x: "相关性优先" if x=="relevance" else "最新日期优先")
    max_num = st.number_input("展示条数", 5, 50, 10)

st.title("🔬 BioGemini Pro")
st.markdown("##### 结合 PubMed 实时检索与 Gemini 1.5 深度分析的学术助手")

col_input, col_btn = st.columns([6, 1])
with col_input:
    user_query = st.text_input("", placeholder="输入你的研究领域或关键词...", label_visibility="collapsed")
with col_btn:
    search_trigger = st.button("检索")

if user_query or search_trigger:
    with st.spinner("🔍 正在扫描 PubMed..."):
        ids = search_pubmed_advanced(user_query, years=search_years, max_results=max_num, sort=search_sort)
    
    if not ids:
        st.warning("未能检索到相关结果。")
    else:
        st.success(f"已为您精选 {len(ids)} 篇文献")
        for pmid in ids:
            title, abstract, year = get_details(pmid)
            if not title: continue
            
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
            
            btn_col, _ = st.columns([1, 3])
            with btn_col:
                if st.button("✨ AI 深度分析", key=f"ai_{pmid}"):
                    # --- 修正点：调用前检查 model 是否存在 ---
                    if model is None:
                        st.error("❌ AI 模型未就绪，请检查 API Key 或侧边栏报错信息。")
                    else:
                        with st.spinner("AI 正在分析..."):
                            prompt = f"作为学术专家，请分析此摘要并用中文输出：1.【中文标题】2.【核心结论】3.【专属 Insight】。内容：{abstract}"
                            try:
                                response = model.generate_content(prompt)
                                st.markdown(f'<div class="ai-box">{response.text}</div>', unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"分析失败: {e}")
            st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2024 BioGemini | 提升科研效率的智能底座")
