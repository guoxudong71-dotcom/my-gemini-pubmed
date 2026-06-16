import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
import io

# 1. 页面基本配置
st.set_page_config(page_title="BioGemini Pro - 智能文献调研站", page_icon="🧬", layout="wide")

# 2. 自定义 CSS
st.markdown("""
    <style>
    .stApp { background-color: transparent; }
    .stButton>button { 
        width: 100%; border-radius: 8px; border: 1px solid #4A90E2; 
        color: #4A90E2; background-color: transparent; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4A90E2; color: white; }
    .paper-card { 
        padding: 24px; border-radius: 12px; background-color: rgba(128, 128, 128, 0.05); 
        border: 1px solid rgba(128, 128, 128, 0.2); margin-bottom: 20px; 
        transition: transform 0.2s ease-in-out; position: relative;
    }
    .paper-card:hover { transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.1); border-color: #4A90E2; }
    
    .new-tag {
        position: absolute; top: 10px; right: 10px;
        background-color: #FFD700; color: #333; padding: 2px 8px;
        border-radius: 4px; font-size: 0.75rem; font-weight: bold;
    }

    .paper-title { font-size: 1.3rem; font-weight: 600; margin-bottom: 10px; line-height: 1.4; }
    .year-tag { background-color: #4A90E2; color: white; padding: 2px 10px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-right: 10px; }
    .ai-box { background-color: rgba(74, 144, 226, 0.1); padding: 25px; border-left: 6px solid #4A90E2; border-radius: 8px; margin: 15px 0; width: 100%; line-height: 1.7; }
    </style>
    """, unsafe_allow_html=True)

# 3. 配置 Gemini
api_key = st.secrets.get("GEMINI_API_KEY")
model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = next((m for m in available_models if 'gemini-1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(selected_model)
        st.sidebar.success(f"✅ 已连接: {selected_model}")
    except Exception as e:
        st.sidebar.error(f"❌ 初始化失败: {e}")

# 4. 辅助函数
def search_pubmed_advanced(query, years=5, max_results=10, sort="relevance", days_limit=None):
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    if days_limit:
        advanced_query = f"{query} AND (\"last {days_limit} days\"[Filter])"
    else:
        current_year = datetime.now().year
        min_year = current_year - years
        advanced_query = f"({query}) AND ({min_year}:{current_year}[DP])"
    
    params = {"db": "pubmed", "term": advanced_query, "retmax": max_results, "retmode": "json", "sort": sort}
    try:
        r = requests.get(search_url, params=params, timeout=10)
        return r.json().get("esearchresult", {}).get("idlist", [])
    except: return []

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
    except: return None, None, None

def create_word_doc(title, pmid, year, analysis_text):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(11)
    style.font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    header = doc.add_heading('BioGemini 文献分析报告', 0)
    for run in header.runs:
        run.font.name = 'Times New Roman'
        run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    p = doc.add_paragraph()
    p.add_run('文献标题: ').bold = True
    p.add_run(title)
    
    p2 = doc.add_paragraph()
    p2.add_run('PMID: ').bold = True
    p2.add_run(f"{pmid}  |  ")
    p2.add_run('年份: ').bold = True
    p2.add_run(year)
    
    doc.add_heading('AI 深度分析结果', level=1)
    for line in analysis_text.split('\n'):
        if line.strip():
            para = doc.add_paragraph(line)
            for run in para.runs:
                run.font.name = 'Times New Roman'
                run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
                
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

# 5. 界面布局
with st.sidebar:
    st.markdown("### 🧬 追踪控制台")
    is_tracking = st.toggle("🛰️ 开启主题自动追新")
    track_days = st.select_slider("追新频率", options=[1, 3, 7, 30], value=7, format_func=lambda x: f"最近 {x} 天") if is_tracking else None
    
    st.markdown("---")
    search_years = st.slider("常规时间跨度", 1, 20, 5)
    search_sort = st.selectbox("排序规则", ["relevance", "pub_date"], format_func=lambda x: "相关性优先" if x=="relevance" else "最新日期优先")
    max_num = st.number_input("展示条数", 5, 50, 10)

st.title("🔬 BioGemini Pro")
st.markdown("##### 结合 PubMed 实时检索与 Gemini 1.5 深度分析的学术助手")

if is_tracking:
    st.info(f"✨ 当前处于追踪模式：监控最近 {track_days} 天的更新")

user_query = st.text_input("", placeholder="输入研究关键词...", label_visibility="collapsed")

if user_query:
    with st.spinner("🚀 正在为您扫描数据库..."):
        ids = search_pubmed_advanced(user_query, years=search_years, max_results=max_num, sort=search_sort, days_limit=track_days)
    
    if ids:
        st.success(f"已为您精选 {len(ids)} 篇文献")
        for pmid in ids:
            title, abstract, year = get_details(pmid)
            if not title: continue
            
            # --- 核心修复：确保 HTML 标签正确渲染，不再显示为代码 ---
            tag_html = f'<div class="new-tag">NEW</div>' if is_tracking else ''
            
            card_html = f"""
            <div class="paper-card">
                {tag_html}
                <span class="year-tag">{year}</span>
                <span style="opacity: 0.7; font-size: 0.85rem;">PMID: {pmid}</span>
                <div class="paper-title">{title}</div>
                <div style="margin-top: 10px;">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #4A90E2;">🔗 查看原文 (PubMed)</a>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            # --- 分析按钮 ---
            btn_col, _ = st.columns([1.5, 5])
            with btn_col:
                analyze_btn = st.button("✨ 深度分析摘要", key=f"ai_{pmid}")
            
            if analyze_btn:
                if model:
                    with st.spinner("AI 正在深度研读中..."):
                        prompt = f"针对以下摘要进行深度分析并用中文回答：1.【中文标题翻译】 2.【核心结论】 3.【亮点与局限】。内容：{abstract}"
                        try:
                            response = model.generate_content(prompt)
                            ai_content = response.text
                            st.markdown(f'<div class="ai-box">{ai_content}</div>', unsafe_allow_html=True)
                            
                            docx_file = create_word_doc(title, pmid, year, ai_content)
                            st.download_button("📥 下载 Word 报告", docx_file, f"Analysis_{pmid}.docx", key=f"dl_{pmid}")
                        except Exception as e: st.error(f"分析失败: {e}")
            st.markdown("<hr style='opacity: 0.1; margin: 20px 0;'>", unsafe_allow_html=True)
    else:
        st.warning("暂未发现相关文献。")

st.markdown("---")
st.caption("© 2026 BioGemini | 自动追踪与智能分析")
