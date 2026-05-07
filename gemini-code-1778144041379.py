import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET

# 页面配置
st.set_page_config(page_title="Gemini PubMed Helper", page_icon="🔬")

# 尝试获取 API Key
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("请在 Streamlit 控制台配置 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

def search_pubmed(query, max_results=10):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax={max_results}&retmode=json"
    return requests.get(url).json().get("esearchresult", {}).get("idlist", [])

def get_details(pmid):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    root = ET.fromstring(requests.get(url).content)
    title = root.find(".//ArticleTitle").text if root.find(".//ArticleTitle") is not None else "No Title"
    abstracts = root.findall(".//AbstractText")
    abstract_text = " ".join([n.text for n in abstracts if n.text])
    return title, abstract_text

st.title("🔬 PubMed + Gemini 智能分析站")
query = st.text_input("输入关键词搜索 PubMed 论文：", placeholder="例如: CRISPR gene editing")

if query:
    ids = search_pubmed(query)
    for pmid in ids:
        title, abstract = get_details(pmid)
        with st.expander(f"📙 {title}"):
            st.write(f"**PubMed ID:** `{pmid}`")
            st.write(f"**原文链接:** [点击跳转](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
            if st.button("✨ 使用 Gemini 深度分析", key=pmid):
                with st.spinner("AI 正在分析摘要并提取 Insight..."):
                    prompt = f"请分析以下论文摘要。1.中文标题 2.一句话核心结论 3.该研究对科研人员的启发。内容如下：{abstract}"
                    response = model.generate_content(prompt)
                    st.info(response.text)