import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 页面基本配置
st.set_page_config(page_title="BioGemini Pro - 智能文献调研站", page_icon="🧬", layout="wide")

# 2. 自定义 CSS：适配深浅模式、全宽显示、以及新增的卡片悬停动效
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

    /* 论文卡片容器 - 增加了 hover 浮起特效 */
    .paper-card { 
        padding: 24px; 
        border-radius: 12px; 
        background-color: rgba(128, 128, 128, 0.05); 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        margin-bottom: 20px; 
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .paper-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-color: #4A90E2;
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

    /* AI 分析框样式 - 适配深浅模式 & 全宽显示 */
    .ai-box {
        background-color: rgba(74, 144, 226, 0.1); 
        padding: 25px; 
        border-left: 6px solid #4A90E2; 
        border-radius: 8px;
        margin-top: 15px;
        margin-bottom: 15px;
        width: 100%; 
        line-height: 1.7;
        font-size: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 配置 Gemini 模型
api_key = st.secrets.get("GEMINI_API_KEY")
model = None

if not api_key:
    st.error("🔑 未在 Secrets 中找到 GEMINI_API_KEY，请检查配置。")
else:
    try:
        genai.configure(api_key=api_key)
        # 获取可用模型列表并智能选择
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
        st.error("❌ 模型未连接")
    
    search_years = st.slider("时间跨度 (近 X 年)", 1, 20, 5)
    search_sort = st.selectbox("排序规则", ["relevance", "pub_date"], format_func=lambda x: "相关性优先" if x=="relevance" else "最新日期优先")
    max_num = st.number_input("展示条数", 5, 50, 10)

st.title("🔬 BioGemini Pro")
st.markdown("##### 结合 PubMed 实时检索与 Gemini 1.5 深度分析的学术助手")

user_query = st.text_input("", placeholder="输入研究领域或关键词 (例如: RSV prevention)...", label_visibility="collapsed")

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
            
            # --- 分析按钮与展示逻辑 ---
            btn_col, _ = st.columns([1.5, 5])
            with btn_col:
                analyze_btn = st.button("✨ 深度分析摘要", key=f"ai_{pmid}")
            
            # 结果展示与导出
            if analyze_btn:
                if not model:
                    st.error("AI 模型未就绪，请检查侧边栏状态。")
                else:
                    with st.spinner("Gemini 正在分析中..."):
                        prompt = f"你是一位资深生物医学专家。请针对以下摘要进行深度分析并用中文回答：1.【中文标题翻译】 2.【核心结论总结】 3.【研究亮点与局限】。内容如下：{abstract}"
                        try:
                            response = model.generate_content(prompt)
                            ai_content = response.text
                            
                            # 展示分析结果 (全宽)
                            st.markdown(f'<div class="ai-box">{ai_content}</div>', unsafe_allow_html=True)
                            
                            # 准备导出数据
                            export_data = f"""# BioGemini 文献分析报告
## 标题: {title}
* **年份**: {year}
* **PMID**: {pmid}
* **链接**: https://pubmed.ncbi.nlm.nih.gov/{pmid}/

---
{ai_content}

---
*Generated by BioGemini Pro*
"""
                            # 放置下载按钮
                            st.download_button(
                                label="📥 下载此篇分析 (Markdown)",
                                data=export_data,
                                file_name=f"Analysis_{pmid}.md",
                                mime="text/markdown",
                                key=f"dl_{pmid}"
                            )
                            
                        except Exception as e:
                            st.error(f"分析失败: {e}")
            
            st.markdown("<hr style='opacity: 0.1; margin: 20px 0;'>", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2026 BioGemini | 助力学术调研与文献理解")
