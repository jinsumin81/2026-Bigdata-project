import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from src.data_loader import load_data
from src.features import clean, add_features

st.title("📊 EDA — 데이터 살펴보기")

df = add_features(clean(load_data()))

# --- 1. 기본 정보 ---
st.header("1. 데이터 개요")
c1, c2, c3, c4 = st.columns(4)
c1.metric("총 행 수",        f"{len(df):,}")
c2.metric("기간 범위",       f"{df['기간'].dt.strftime('%Y.%m').min()} ~ {df['기간'].dt.strftime('%Y.%m').max()}")
c3.metric("직종 중분류 수",  f"{df['직종_중분류'].nunique()}")
c4.metric("직종 소분류 수",  f"{df['직종_소분류'].nunique()}")

st.subheader("미리보기")
with st.expander("필터 옵션", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        years = ["전체"] + sorted(df["연도"].unique().tolist())
        sel_year = st.selectbox("연도", years)
    with fc2:
        cats = ["전체"] + sorted(df["직종_중분류"].unique().tolist())
        sel_cat = st.selectbox("직종 중분류", cats)
    with fc3:
        sort_col = st.selectbox("정렬 기준", ["기간", "구인인원", "구직건수", "취업건수", "경쟁률", "취업률"])
        sort_asc = st.toggle("오름차순", value=False)

preview = df.copy()
if sel_year != "전체":
    preview = preview[preview["연도"] == sel_year]
if sel_cat != "전체":
    preview = preview[preview["직종_중분류"] == sel_cat]
preview = preview.sort_values(sort_col, ascending=sort_asc)

st.caption(f"필터 결과: {len(preview):,}행")
st.dataframe(preview.head(50), use_container_width=True)

# --- 2. 요약 통계 ---
st.header("2. 요약 통계")
st.dataframe(
    df[["구인인원", "구직건수", "취업건수", "취업률", "경쟁률"]].describe().T,
    use_container_width=True,
)

# --- 3. 결측치 ---
st.header("3. 결측치")
na = df.isna().sum()
na = na[na > 0].sort_values(ascending=False)
if len(na) == 0:
    st.success("결측치 없음 ✅")
else:
    st.bar_chart(na)

# --- 4. 발견 사실 메모 ---
st.header("4. 내가 발견한 것")
st.info("""
- 전체 기간(2021.01 ~ 2025.12) 누적 구인인원 약 1,300만 명, 구직건수 약 2,400만 건
- 구직건수가 구인인원보다 약 1.8배 많아 전반적으로 구직 경쟁이 치열함
- 직종별 구인 규모 편차가 크며, 특정 중분류에 구인이 집중되어 있음
""")