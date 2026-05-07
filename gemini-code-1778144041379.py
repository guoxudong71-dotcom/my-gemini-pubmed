import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET

# 1. 页面基本配置
st.set_page_config(
    page_title="Gemini PubMed AI 分析站",
    page_icon="🔬",
    layout="wide"
)

# 2. 从 Secrets 获取 API Key
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 未在 Secrets 中找到 GEMINI_API_KEY，请检查配置。")
    st.stop()

# 3. 配置 Gemini 模型
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
except Exception as e:
    st.error(f"❌ Gemini 配置失败: {e}")

# --- 功能函数 ---

def search_pubmed(query, max_results=10):
    """搜索 PubMed 并返回 ID 列表"""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    }
    try:
        r = requests.get(search_url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        st.error(f"搜索出错: {e}")
        return []

def get_details(pmid):
    """获取单篇文献的标题和摘要"""
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    try:
        r = requests.get(fetch_url, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        
        # 提取标题
        title_node = root.find(".//ArticleTitle")
        title = title_node.text if title_node is not None else "No Title Found"
        
        # 提取摘要（合并多个 AbstractText 节点）
        abstract_nodes = root.findall(".//AbstractText")
        abstract_text = " ".join([n.text for n in abstract_nodes if n.text])
        if not abstract_text:
            abstract_text = "No abstract available."
            
        return title, abstract_text
    except Exception as e:
        return f"解析错误 (ID: {pmid})", f"无法获取摘要内容: {str(e)}"

# --- 界面展示 ---

st.title("🔬 PubMed + Gemini 智能分析站")
st.markdown("---")

# 侧边栏设置
with st.sidebar:
    st.header("搜索设置")
    max_num = st.slider("最大搜索结果数", 5, 50, 10)
    st.info("输入关键词，点击展开文献，然后让 Gemini 为你解析。")

# 搜索框
query = st.text_input("🔍 输入科研关键词：", placeholder="例如: Solid-state battery electrolyte stability")

if query:
    with st.spinner("正在 PubMed 中检索..."):
        ids = search_pubmed(query, max_results=max_num)
    
    if not ids:
        st.warning("⚠️ 未找到相关文献，请尝试更换关键词。")
    else:
        st.subheader(f"找到 {len(ids)} 篇相关文献：")
        
        for pmid in ids:
            title, abstract = get_details(pmid)
            
            # 使用 Expander 折叠显示
            with st.expander(f"📙 {title}"):
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.write(f"**PMID:** `{pmid}`")
                with col2:
                    st.write(f"**原文链接:** [点击跳转 PubMed](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
                
                # 分析按钮
                if st.button(f"✨ 使用 Gemini 深度分析", key=f"btn_{pmid}"):
                    with st.spinner("AI 正在阅读摘要..."):
                        prompt = f"""
                        你是一个专业的科研专家。请针对以下文献摘要进行深度分析并用中文回答：
                        1. 【中文标题】：准确翻译。
                        2. 【一句话总结】：核心结论是什么。
                        3. 【专属 Insight】：该研究对相关领域工作的具体启发或局限。
                        
                        文献内容：
                        {abstract}
                        """
                        try:
                            response = model.generate_content(prompt)
                            st.markdown("---")
                            st.success("✅ Gemini 分析结果：")
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"Gemini 分析时出错: {e}")

st.markdown("---")
st.caption("Powered by Streamlit | PubMed API | Google Gemini 1.5 Flash")
