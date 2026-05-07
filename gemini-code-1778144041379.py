import streamlit as st
import requests
import google.generativeai as genai
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 页面配置：使用宽屏模式和自定义主题
st.set_page_config(page_title="BioGemini Pro - 智能文献站", page_icon="🧬", layout="wide")

# 自定义 CSS 让排版更像高端科研工具
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 20px; border: 1px solid #4A90E2; color: #4A90E2; }
    .stButton>button:hover { background-color: #4A90E2; color: white; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    .paper-card { padding: 1.5rem; border-radius: 10px; background-color: white; border: 1px solid #e1e4e8; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_stdio=True)

# 2. 密钥检查
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("🔑 请在 Secrets 中配置 GEMINI_API_KEY")
    st.stop()

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

# --- 核心逻辑：PubMed 增强搜索 ---
def search_pubmed_advanced(query, years=5, max_results=10, sort="relevance"):
    # 构建高级检索词：限定年份和布尔逻辑
    current_year = datetime.now().year
    min_year = current_year - years
    advanced_query = f"({query}) AND ({min_year}:{current_year}[DP])"
    
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": advanced_query,
        "retmax": max_results,
        "retmode": "json",
        "sort": sort
    }
    r = requests.get(search_url, params=params)
    return r.json().get("esearchresult", {}).get("idlist", [])

def get_details(pmid):
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    try:
        r = requests.get(fetch_url, timeout=10)
        root = ET.fromstring(r.content)
        title = root.find(".//ArticleTitle").text if root.find(".//ArticleTitle") is not None else "No Title"
        abstracts = root.findall(".//AbstractText")
        abstract_text = " ".join([n.text for n in abstracts if n.text])
        # 提取年份
        pub_date = root.find(".//PubDate/Year")
        year = pub_date.text if pub_date is not None else "N/A"
        return title, abstract_text, year
    except:
        return None, None, None

# --- 界面排版 ---

# 侧边栏：高级检索面板
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/dna-helix.png", width=80)
    st.title("高级检索设置")
    st.markdown("---")
    search_years = st.slider("文献年份范围 (近 X 年)", 1, 20, 5)
    search_sort = st.selectbox("排序方式", ["relevance", "pub_date"], format_func=lambda x: "相关性" if x=="relevance" else "最新日期")
    max_num = st.number_input("获取条数", 5, 50, 10)
    st.markdown("---")
    st.caption("AI 模型状态: 🟢 已就绪")

# 主界面
st.title("🔬 BioGemini Pro")
st.subheader("PubMed 增强型智能学术调研平台")

# 搜索行
col_search, col_btn = st.columns([5, 1])
with col_search:
    user_query = st.text_input("", placeholder="输入研究关键词 (例如: Single cell RNA sequencing Alzheimer's)", label_visibility="collapsed")
with col_btn:
    search_trigger = st.button("开始检索")

if user_query or search_trigger:
    with st.spinner("正在扫描 PubMed 数据库并构建知识索引..."):
        ids = search_pubmed_advanced(user_query, years=search_years, max_results=max_num, sort=search_sort)
    
    if not ids:
        st.warning("未能找到匹配的文献，请尝试缩短搜索词或扩大年份范围。")
    else:
        st.info(f"💡 找到 {len(ids)} 篇来自近 {search_years} 年的高质量文献")
        
        # 结果展示：使用卡片排版
        for pmid in ids:
            title, abstract, year = get_details(pmid)
            if not title: continue
            
            with st.container():
                st.markdown(f"""
                <div class="paper-card">
                    <span style="color: #4A90E2; font-weight: bold;">[{year}]</span>
                    <h3 style="margin-top: 0;">{title}</h3>
                    <p style="font-size: 0.8rem; color: #666;">PMID: {pmid} | <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank">View on PubMed</a></p>
                </div>
                """, unsafe_allow_stdio=True)
                
                # 交互按钮
                btn_col1, btn_col2 = st.columns([1, 2])
                with btn_col1:
                    if st.button("🧠 AI 深度分析", key=f"ai_{pmid}"):
                        with st.spinner("Gemini 正在研读..."):
                            prompt = f"你是一个顶级科学家。请分析：1.中文翻译标题 2.核心结论 3.研究的局限性与我的机会。摘要：{abstract}"
                            response = model.generate_content(prompt)
                            st.markdown(f"""
                            <div style="background-color: #eef6ff; padding: 15px; border-left: 5px solid #4A90E2; border-radius: 5px;">
                                {response.text}
                            </div>
                            """, unsafe_allow_stdio=True)
                st.markdown("<br>", unsafe_allow_stdio=True)

st.markdown("---")
st.center = st.caption("BioGemini v2.0 | 专注提升学术生产力")
