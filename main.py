import streamlit as st
import pandas as pd
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
# 한글 파일명 안전 처리
# ==================================================
def norm(text):
    return unicodedata.normalize("NFC", text)

def find_file(path: Path, name: str):
    for f in path.iterdir():
        if norm(f.name) == norm(name):
            return f
    return None

# ==================================================
# 데이터 로딩
# ==================================================
@st.cache_data
def load_environment():
    data_dir = Path("data")
    env = {}
    for school in ["송도고", "하늘고", "아라고", "동산고"]:
        file = find_file(data_dir, f"{school}_환경데이터.csv")
        if file is None:
            st.error(f"환경 데이터 누락: {school}")
            return None
        df = pd.read_csv(file)
        df["학교"] = school
        env[school] = df
    return env

@st.cache_data
def load_growth():
    data_dir = Path("data")
    file = find_file(data_dir, "4개교_생육결과데이터.xlsx")
    if file is None:
        st.error("생육 결과 파일 누락")
        return None

    xls = pd.ExcelFile(file)
    growth = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["학교"] = sheet
        growth[sheet] = df
    return growth

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment()
    growth_data = load_growth()

if env_data is None or growth_data is None:
    st.stop()

# ==================================================
# 사이드바
# ==================================================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체", "송도고", "하늘고", "아라고", "동산고"]
)

# ==================================================
# 데이터 병합 (학교 단위 평균 생중량)
# ==================================================
env_all = pd.concat(env_data.values(), ignore_index=True)
growth_all = pd.concat(growth_data.values(), ignore_index=True)

school_mean_weight = (
    growth_all.groupby("학교")["생중량(g)"]
    .mean()
    .reset_index()
)

merged = env_all.merge(school_mean_weight, on="학교")

# ==================================================
# 제목
# ==================================================
st.title("🌱 나도수영 생장 최적 환경조건 분석")

tab1, tab2, tab3 = st.tabs([
    "📈 환경 요인–생중량 관계",
    "📋 환경 변수별 최적 조건",
    "🧠 연구 결론·의의·한계"
])

# ==================================================
# TAB 1 : 꺾은선 + 최적 지점 표시
# ==================================================
with tab1:
    st.subheader("환경 조건 변화에 따른 평균 생중량")

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
        temp = merged.groupby(col)["생중량(g)"].mean().reset_index()
        best = temp.loc[temp["생중량(g)"].idxmax()]

        fig.add_trace(
            go.Scatter(
                x=temp[col],
                y=temp["생중량(g)"],
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
# TAB 2 : 변수별 최적 조건 표
# ==================================================
with tab2:
    st.subheader("환경 변수별 평균 생중량 최댓값 조건")

    rows = []
    for col, label in variables.items():
        temp = merged.groupby(col)["생중량(g)"].mean().reset_index()
        best = temp.loc[temp["생중량(g)"].idxmax()]
        rows.append([label, round(best[col], 3), round(best["생중량(g)"], 3)])

    result_df = pd.DataFrame(
        rows,
        columns=["환경 변수", "생중량 최댓값이 나타난 조건", "평균 생중량(g)"]
    )

    st.dataframe(result_df, use_container_width=True)

    buffer = io.BytesIO()
    result_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "표 다운로드 (XLSX)",
        data=buffer,
        file_name="환경변수별_최적조건.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ==================================================
# TAB 3 : 결론 · 의의 · 한계
# ==================================================
with tab3:
    st.markdown("""
### 🔍 연구 결론

본 연구에서는 학교별로 상이한 환경 조건에서 재배된 나도수영의 생육 데이터를 분석하여, 생중량을 기준으로 최적 생육 환경을 도출하고자 하였다.
Streamlit을 활용한 데이터 분석 결과, 전기전도도(EC) 2.0 조건에서 평균 생중량이 가장 높고 개체 간 편차가 작아 생육이 가장 안정적으로 나타났다. 또한 pH는 중성에 가까운 조건에서 생육 안정성이 높았으며, 습도가 과도하게 높아질 경우 생중량의 변동성이 증가하는 경향이 확인되었다. 반면 온도는 본 연구 범위 내에서는 생중량에 미치는 영향이 상대적으로 제한적이었다.
이를 종합하면, 나도수영의 안정적인 생장을 위해서는 중간 수준의 EC, 중성 pH, 과도하지 않은 습도 유지가 핵심 조건임을 알 수 있다.

---

### 🌱 연구의 의의

- 실측 환경 데이터와 생육 데이터를 결합한 **정량적 분석**
- 환경 요인을 개별적으로 분리하여 생육과의 관계를 분석
- 극지 식물 재배 환경 설계에 활용 가능한 기초 자료 제시

---

### ⚠ 연구의 한계

- 생육 데이터가 시간 정보와 직접 연결되지 못함
- 학교 단위 실험으로 EC 외 환경 요인의 완전한 통제가 어려움
- 향후 동일 조건 반복 실험을 통한 검증 필요
""")

