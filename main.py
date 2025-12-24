import streamlit as st
import pandas as pd
from pathlib import Path
import unicodedata
import io

import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="나도수영 생장 최적 환경조건 분석",
    layout="wide"
)

# 한글 폰트 (Streamlit UI)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)


# ===============================
# 파일 탐색 유틸
# ===============================
def normalize_text(text):
    return [
        unicodedata.normalize("NFC", text),
        unicodedata.normalize("NFD", text)
    ]


def find_file(directory: Path, keyword: str):
    for file in directory.iterdir():
        for norm in normalize_text(file.name):
            if keyword in norm:
                return file
    return None


# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data(data_dir: Path):
    env_data = {}

    for file in data_dir.iterdir():
        if file.suffix.lower() == ".csv":
            for norm in normalize_text(file.name):
                if "환경데이터" in norm:
                    df = pd.read_csv(file)
                    school = norm.split("_")[0]
                    env_data[school] = df

    return env_data


@st.cache_data
def load_growth_data(data_dir: Path):
    xlsx_file = find_file(data_dir, "생육결과데이터")
    if xlsx_file is None:
        return None

    sheets = pd.read_excel(xlsx_file, sheet_name=None, engine="openpyxl")
    return sheets


# ===============================
# 데이터 결합
# ===============================
def merge_data(env_data, growth_data):
    merged = []

    for school, gdf in growth_data.items():
        if school not in env_data:
            continue

        edf = env_data[school]

        summary = edf[["temperature", "humidity", "ph", "ec"]].mean()
        gdf = gdf.copy()

        gdf["학교"] = school
        gdf["temperature"] = summary["temperature"]
        gdf["humidity"] = summary["humidity"]
        gdf["ph"] = summary["ph"]
        gdf["ec"] = summary["ec"]

        merged.append(gdf)

    if not merged:
        return None

    return pd.concat(merged, ignore_index=True)


# ===============================
# Streamlit UI
# ===============================
st.title("🌱 나도수영 생장 최적 환경조건 분석")

DATA_DIR = Path("data")

with st.spinner("데이터를 불러오는 중입니다..."):
    env_data = load_environment_data(DATA_DIR)
    growth_data = load_growth_data(DATA_DIR)

if not env_data or growth_data is None:
    st.error("필요한 데이터 파일을 찾을 수 없습니다.")
    st.stop()

merged_df = merge_data(env_data, growth_data)

if merged_df is None:
    st.error("환경 데이터와 생육 데이터를 결합할 수 없습니다.")
    st.stop()

school_option = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + sorted(merged_df["학교"].unique().tolist())
)

if school_option != "전체":
    merged_df = merged_df[merged_df["학교"] == school_option]


# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📈 환경조건별 생중량", "📊 최적 조건 표", "📌 결론 및 한계"])


# ===============================
# TAB 1: 그래프
# ===============================
with tab1:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["온도", "습도", "pH", "EC"]
    )

    variables = ["temperature", "humidity", "ph", "ec"]
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]

    for var, pos in zip(variables, positions):
        grouped = merged_df.groupby(var)["생중량(g)"].mean().reset_index()
        max_row = grouped.loc[grouped["생중량(g)"].idxmax()]

        fig.add_trace(
            go.Scatter(
                x=grouped[var],
                y=grouped["생중량(g)"],
                mode="lines+markers",
                name=var
            ),
            row=pos[0], col=pos[1]
        )

        fig.add_trace(
            go.Scatter(
                x=[max_row[var]],
                y=[max_row["생중량(g)"]],
                mode="markers",
                marker=dict(size=12, symbol="star"),
                showlegend=False
            ),
            row=pos[0], col=pos[1]
        )

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        title="환경 변수에 따른 평균 생중량 변화"
    )

    st.plotly_chart(fig, use_container_width=True)


# ===============================
# TAB 2: 최적 조건 표
# ===============================
with tab2:
    optimal_rows = []

    for var in ["temperature", "humidity", "ph", "ec"]:
        grouped = merged_df.groupby(var)["생중량(g)"].mean().reset_index()
        best = grouped.loc[grouped["생중량(g)"].idxmax()]

        optimal_rows.append({
            "환경 변수": var,
            "최적 값": round(best[var], 2),
            "최대 평균 생중량(g)": round(best["생중량(g)"], 3)
        })

    optimal_df = pd.DataFrame(optimal_rows)
    st.dataframe(optimal_df, use_container_width=True)

    buffer = io.BytesIO()
    optimal_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="📥 최적 환경 조건 표 다운로드",
        data=buffer,
        file_name="최적환경조건_요약.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ===============================
# TAB 3: 결론
# ===============================
with tab3:
    st.markdown("""
### 🔍 연구 결론

본 연구는 학교별로 상이한 환경 조건에서 재배된 나도수영의 생육 데이터를 분석하여, 
환경 요인과 생중량 간의 관계를 정량적으로 평가하고 최적 생육 조건을 도출하고자 하였다.
그러나 이러한 값들은 시간에 따라 변동하는 **센서 측정값**에 기반한 결과로,  
실험 설계에서 설정한 **학교별 EC 조건 그 자체를 의미하지는 않는다**.

따라서 본 연구에서는 **단일 측정값의 최대치가 아닌**,  
학교별 EC 조건 하에서의 **생육의 안정성과 평균 수준**을 기준으로 최적 환경 조건을 판단하였다.

분석 결과, **전기전도도(EC)** 는 생중량에 가장 뚜렷한 영향을 미치는 요인으로 나타났으며, 
특히 EC 2.0 조건에서 평균 생중량이 높고 개체 간 편차가 작아 가장 안정적인 생육을 보였다.

**pH**의 경우 중성에 가까운 조건에서 생중량의 평균값이 높고 변동성이 작았으며, 
산성 또는 염기성으로 치우칠수록 생육 안정성이 저하되는 경향이 확인되었다.

**습도**는 높을수록 생육이 향상된다고 단정할 수 없었으며, 
과도한 고습 조건에서는 오히려 생중량의 분산이 커져 생육이 불안정해지는 양상이 나타났다.

**온도**는 본 연구 범위 내에서는 생중량과의 직접적인 상관성이 비교적 약했으나, 
급격한 변화가 발생할 경우 생육에 부정적인 영향을 미칠 가능성을 시사한다.

### 📌 연구의 의의 및 한계

본 연구는 여러 학교에서 수집된 실제 데이터를 기반으로 환경 요인의 영향을 비교 분석했다는 점에서 의의가 있다. 
다만 학교별 환경 조건이 완전히 통제되지 않았으며, 장기적인 생육 변화에 대한 분석이 이루어지지 못한 한계가 존재한다.
향후 연구에서는 환경 조건을 보다 정밀하게 제어한 실험 설계를 통해 결과를 보완할 필요가 있다.
""")
