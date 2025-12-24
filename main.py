import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ---------------------------
# 기본 설정
# ---------------------------
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
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

# ---------------------------
# 유틸: 한글 파일 안전 탐색
# ---------------------------
def normalize(text):
    return unicodedata.normalize("NFC", text)

def find_file(directory: Path, target_name: str):
    target_nfc = normalize(target_name)
    for f in directory.iterdir():
        if normalize(f.name) == target_nfc:
            return f
    return None

# ---------------------------
# 데이터 로딩
# ---------------------------
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    files = {}
    for school in ["송도고", "하늘고", "아라고", "동산고"]:
        file = find_file(data_dir, f"{school}_환경데이터.csv")
        if file is None:
            st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {school}")
            return None
        df = pd.read_csv(file)
        df["학교"] = school
        files[school] = df
    return files

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    file = find_file(data_dir, "4개교_생육결과데이터.xlsx")
    if file is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    xls = pd.ExcelFile(file)
    data = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["학교"] = sheet
        data[sheet] = df
    return data

with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ---------------------------
# EC 조건
# ---------------------------
EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ---------------------------
# 사이드바
# ---------------------------
st.sidebar.title("🏫 학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체", "송도고", "하늘고", "아라고", "동산고"]
)

# ---------------------------
# 제목
# ---------------------------
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# TAB 1: 실험 개요
# =====================================================
with tab1:
    st.subheader("🔬 연구 배경 및 목적")
    st.markdown(
        """
        본 연구는 **극지식물 생육에 적합한 EC(Electrical Conductivity) 농도**를 규명하기 위해  
        4개 고등학교에서 서로 다른 EC 조건 하에서 환경 요인과 생육 결과를 비교 분석하였다.
        """
    )

    summary = []
    for school, df in growth_data.items():
        summary.append([
            school,
            EC_MAP.get(school),
            len(df)
        ])

    summary_df = pd.DataFrame(summary, columns=["학교", "EC 목표", "개체수"])
    st.dataframe(summary_df, use_container_width=True)

    total_plants = sum(len(df) for df in growth_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    avg_weight_by_ec = (
        pd.concat(growth_data.values())
        .groupby("학교")["생중량(g)"].mean()
    )
    optimal_school = avg_weight_by_ec.idxmax()
    optimal_ec = EC_MAP[optimal_school]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_plants)
    c2.metric("평균 온도 (°C)", f"{avg_temp:.1f}")
    c3.metric("평균 습도 (%)", f"{avg_hum:.1f}")
    c4.metric("최적 EC", f"{optimal_ec} (하늘고)")

# =====================================================
# TAB 2: 환경 데이터
# =====================================================
with tab2:
    st.subheader("📊 학교별 환경 평균 비교")

    env_all = pd.concat(env_data.values())
    env_mean = env_all.groupby("학교")[["temperature", "humidity", "ph", "ec"]].mean().reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=env_mean["학교"], y=env_mean["temperature"], row=1, col=1)
    fig.add_bar(x=env_mean["학교"], y=env_mean["humidity"], row=1, col=2)
    fig.add_bar(x=env_mean["학교"], y=env_mean["ph"], row=2, col=1)
    fig.add_bar(x=env_mean["학교"], y=env_mean["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(
        x=list(EC_MAP.keys()),
        y=list(EC_MAP.values()),
        name="목표 EC",
        row=2, col=2
    )

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]
        st.subheader(f"⏱️ {school_option} 시계열 변화")

        for col, label in zip(
            ["temperature", "humidity", "ec"],
            ["온도", "습도", "EC"]
        ):
            fig = px.line(df, x="time", y=col)
            if col == "ec":
                fig.add_hline(y=EC_MAP[school_option], line_dash="dash")
            fig.update_layout(font=dict(family="Malgun Gothic"))
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 환경 데이터 원본"):
        st.dataframe(env_all)
        csv = env_all.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, "환경데이터.csv", "text/csv")

# =====================================================
# TAB 3: 생육 결과
# =====================================================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    growth_all = pd.concat(growth_data.values())
    weight_mean = growth_all.groupby("학교")["생중량(g)"].mean().reset_index()

    fig = px.bar(weight_mean, x="학교", y="생중량(g)", color="학교")
    fig.update_layout(font=dict(family="Malgun Gothic"))
    st.plotly_chart(fig, use_container_width=True)

    metrics = growth_all.groupby("학교").agg({
        "생중량(g)": "mean",
        "잎 수(장)": "mean",
        "지상부 길이(mm)": "mean",
        "개체번호": "count"
    }).reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig.add_bar(x=metrics["학교"], y=metrics["생중량(g)"], row=1, col=1)
    fig.add_bar(x=metrics["학교"], y=metrics["잎 수(장)"], row=1, col=2)
    fig.add_bar(x=metrics["학교"], y=metrics["지상부 길이(mm)"], row=2, col=1)
    fig.add_bar(x=metrics["학교"], y=metrics["개체번호"], row=2, col=2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic"),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📦 생중량 분포")
    fig = px.box(growth_all, x="학교", y="생중량(g)")
    fig.update_layout(font=dict(family="Malgun Gothic"))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔗 상관관계 분석")
    col1, col2 = st.columns(2)

    with col1:
        fig = px.scatter(growth_all, x="잎 수(장)", y="생중량(g)", color="학교")
        fig.update_layout(font=dict(family="Malgun Gothic"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(growth_all, x="지상부 길이(mm)", y="생중량(g)", color="학교")
        fig.update_layout(font=dict(family="Malgun Gothic"))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 생육 데이터 원본"):
        st.dataframe(growth_all)

        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
