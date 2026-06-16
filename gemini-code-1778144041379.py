import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
import io

# 1. 页面配置
st.set_page_config(page_title="BioGemini Pro", page_icon="🧬", layout="wide")

# 2. CSS 样式 (保持不变)
st.markdown("""
    <style>
    .paper-card { padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px; background-color: #f9f9f9; }
    .paper-title { font-size: 18px; font-weight: bold; color: #333; }
    .ai-box { background-color: #eef6ff; padding: 20px; border-left: 5px solid #4a90e2; border-radius: 5px; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

# 3. 逻辑函数 (简化部分以确保稳定)
def search_pubmed(query, days_limit=None):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    term = f"{query} AND (\"last {days_limit} days\"[Filter])" if days_limit else query
    params = {"db": "pubmed", "term": term, "retmax": 5, "retmode": "json"}
    try:
        r = requests.get(base_url, params=params)
        return r.json().get("esearchresult", {}).get("idlist", [])
    except: return []

def get_details(pmid):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    try:
        r = requests.get(url)
        root = ET.fromstring(r.content)
        title = root.find(".//ArticleTitle").text if root.find(".//ArticleTitle") is not None else "Untitled"
        abstract = " ".join([n.text for n in root.findall(".//AbstractText") if n.text])
        year = root.find(".//PubDate/Year").text if root.find(".//PubDate/Year") is not None else "N/A"
        return title, abstract, year
    except: return None, None, None

# 4. 主界面
st.title("🧬 BioGemini Pro")
query = st.text_input("输入关键词:")
is_tracking = st.sidebar.checkbox("开启追踪模式")
days = st.sidebar.slider("最近天数", 1, 30, 7) if is_tracking else None

if query:
    ids = search_pubmed(query, days)
    if not ids:
        st.warning("未找到相关文献")
    else:
        for pmid in ids:
            title, abstract, year = get_details(pmid)
            if not title: continue
            
            # 修复核心：确保 HTML 字符串是一个完整的块，并直接传递给 st.markdown
            card_html = f"""
            <div class="paper-card">
                <div class="paper-title">{title}</div>
                <p>PMID: {pmid} | 年份: {year}</p>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank">查看原文</a>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button("深度分析", key=f"btn_{pmid}"):
                with st.spinner("分析中..."):
                    # 这里调用 API
                    st.success("分析结果 (模拟)")
                    st.markdown(f'<div class="ai-box">这里是AI分析的内容...</div>', unsafe_allow_html=True)
