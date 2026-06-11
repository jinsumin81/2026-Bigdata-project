import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd
from src.data_loader import load_data
from src.features import clean, add_features

st.title("EDA — 데이터 살펴보기")

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
        sort_col = st.selectbox("정렬 기준", ["기간", "구인인원", "구직건수", "취업건수", "경쟁률", "취업연결비율"])
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
    df[["구인인원", "구직건수", "취업건수", "취업연결비율", "경쟁률"]].describe().T,
    use_container_width=True,
)

# --- 3. 결측치 ---
st.header("3. 결측치")
na = df.isna().sum()
na = na[na > 0].sort_values(ascending=False)
if len(na) == 0:
    st.success("결측치 없음")
else:
    st.bar_chart(na)

# --- 4. 이상치 탐지 ---
st.header("4. 이상치 탐지 (IQR 방법)")
st.caption("각 수치 컬럼에서 IQR × 1.5 기준을 벗어난 행을 이상치로 판정합니다.")

outlier_cols = ["구인인원", "구직건수", "취업건수", "경쟁률", "취업연결비율"]
outlier_summary = []

for col in outlier_cols:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    out_df = df[(df[col] < lower) | (df[col] > upper)]
    outlier_summary.append({
        "컬럼": col,
        "이상치 행 수": len(out_df),
        "전체 대비(%)": round(len(out_df) / len(df) * 100, 1),
        "하한": round(lower, 2),
        "상한": round(upper, 2),
        "최솟값": round(df[col].min(), 2),
        "최댓값": round(df[col].max(), 2),
    })

st.dataframe(pd.DataFrame(outlier_summary), use_container_width=True)

# 이상치 직종 상세 — 경쟁률 기준
st.subheader("경쟁률 이상치 직종 (상위 10개)")
q1 = df["경쟁률"].quantile(0.25)
q3 = df["경쟁률"].quantile(0.75)
upper_comp = q3 + 1.5 * (q3 - q1)
comp_outliers = (
    df[df["경쟁률"] > upper_comp]
    .groupby("직종_중분류")["경쟁률"]
    .mean()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
    .rename(columns={"경쟁률": "평균 경쟁률"})
)
if not comp_outliers.empty:
    fig_out = px.bar(
        comp_outliers, x="평균 경쟁률", y="직종_중분류", orientation="h",
        title="경쟁률 이상치 직종 (IQR 기준 상한 초과)",
        color="평균 경쟁률", color_continuous_scale="Reds",
    )
    fig_out.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_out, use_container_width=True)
    st.caption("💡 인사이트: 이 직종들은 경쟁률이 평균의 3배 이상으로 사실상 포화 상태다. 추천 모델에서 이 직종을 상위에 올리면 현실 취업 가능성과 괴리가 생기므로, 경쟁률 패널티 가중치(×0.20)를 반영해 점수를 낮추었다.")

# --- 5. 발견 사실 메모 ---
st.header("5. 내가 발견한 것")
st.info("""
- 전체 기간(2021.01 ~ 2025.12) 누적 구인인원 약 1,300만 명, 구직건수 약 2,400만 건
- 구직건수가 구인인원보다 약 1.8배 많아 전반적으로 구직 경쟁이 치열함
- 직종별 구인 규모 편차가 크며, 특정 중분류에 구인이 집중되어 있음
- 경쟁률 컬럼에서 IQR 기준 이상치 직종이 다수 존재하며, 일부 직종은 평균 대비 경쟁률이 수 배 이상 높음
- 취업연결비율은 구직신청 건수 기준이므로 실제 취업률과 다르며, 100%를 초과하는 경우도 있어 해석 시 주의가 필요함
""")
