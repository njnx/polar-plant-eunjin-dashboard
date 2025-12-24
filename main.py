import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ==================================================
# 기본 설정
# ==================================================
st.set_page_config(
    page_title="나도수영 생장 최적 환경조건 분석",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# 한글 파일 안전 탐색
# ==================================================
def normalize(text):
    return unicodedata.normalize("NFC", text)

def find_file(directory: Path, target_name: str):
    target = normalize(target_name)
    for f in directory.iterdir():
        if normalize(f.name) == target:
            return f
    return None

# ==================================================
# 데이터 로딩
# ==================================================
@st.cache_data
def load_env_data():
    data_dir = Path("data")
    env = {}
    for school in ["송도고", "하늘고", "아라고", "동산고"]:
        file = find_file(data_dir, f"{school}_환경데이터.csv")
        if file is None:
            st.error(f"❌ 환경 데이터 파일 누락: {school}")
            return None
        df = pd.read_csv(file)
        df["학교"] = school
        env[school] = df
    return env

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    file = find_file(data_dir, "4개교_생육결과데이터.xlsx")
    if file is None:
        st.error("❌ 생육 결과 파일 누락")
        return None

    xls = pd.ExcelFile(file)
    data = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["학교"] = sheet
        data[sheet] = df
    return data

with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ==================================================
# EC 조건
# ==================================================
EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ==================================================
# 사이드바
# ==================================================
st.sidebar.title("🏫 학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체", "송도고", "하늘고", "아라고", "동산고"]
)

# ==================================================
# 제목
# ==================================================
st.title("🌱 나도수영 생장 최적 환경조건 분석")

tab1, tab2, tab3 = st.tabs(["📈 환경요인–생중량 관계", "📋 최적 조건 요약", "🎯 연구 목적"])

# ==================================================
# TAB 1
# ==================================================
with tab1:
    st.subheader("환경 요인별 생중량 변화")

    env_all = pd.concat(env_data.values())
    growth_all = pd.concat(growth_data.values())

    merged = env_all.merge(
        growth_all.groupby("학교")["생중량(g)"].mean().reset_index(),
        on="학교"
    )

    variables = {
        "temperature": "온도(°C)",
        "humidity": "습도(%)",
        "ph": "pH",
        "ec": "EC"
    }

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=list(variables.values())
    )

    positions = [(1,1), (1,2), (2,1), (2,2)]

    for (col, label), (r, c) in zip(variables.items(), positions):
        mean_df = merged.groupby(col)["생중량(g)"].mean().reset_index()
        best = mean_df.loc[mean_df["생중량(g)"].idxmax()]

        fig.add_trace(
            go.Scatter(
                x=mean_df[col],
                y=mean_df["생중량(g)"],
                mode="lines+markers",
                name=label
            ),
            row=r, col=c
        )

        fig.add_trace(
            go.Scatter(
                x=[best[col]],
                y=[best["생중량(g)"]],
                mode="markers",
                marker=dict(size=12, symbol="star", color="gold"),
                showlegend=False
            ),
            row=r, col=c
        )

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB 2
# ==================================================
with tab2:
    st.subheader("환경 변수별 최적 생중량 조건")

    optimal_rows = []

    for col, label in variables.items():
        temp = merged.groupby(col)["생중량(g)"].mean().reset_index()
        best = temp.loc[temp["생중량(g)"].idxmax()]
        optimal_rows.append([
            label,
            best[col],
            round(best["생중량(g)"], 3)
        ])

    optimal_df = pd.DataFrame(
        optimal_rows,
        columns=["환경 변수", "최적 조건", "평균 생중량(g)"]
    )

    st.dataframe(optimal_df, use_container_width=True)

    buffer = io.BytesIO()
    optimal_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "최적 조건 표 다운로드 (XLSX)",
        data=buffer,
        file_name="최적환경조건_요약.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ==================================================
# TAB 3
# ==================================================
with tab3:
    st.markdown("""
    ### 🎯 연구 목적

    본 연구는 **극지 환경에서도 안정적인 생육을 보이는 나도수영의 최적 생장 조건**을 규명하기 위해 수행되었다.  

    서로 다른 **EC 조건**과 **환경 요인(온도, 습도, pH)**이  
    생중량에 미치는 영향을 비교 분석함으로써,

    - **높은 습도 조건에서는 생육 변동성이 증가**하며  
    - **중성(pH 6–7) 환경에서 생육이 가장 안정적**이고  
    - **EC 2.0 조건에서 생중량이 가장 안정적으로 유지됨**을 확인하는 데 목적이 있다.

    본 결과는 **극지 식물 재배 환경 제어 및 스마트 농업 시스템 설계**의 기초 자료로 활용될 수 있다.
    """)
