import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd
from src.data_loader import load_data
from src.features import clean, add_features

st.title("📈 시각화 — 직종 트렌드 분석")

df = add_features(clean(load_data()))

# --- 그래프 1: 연도별 구인 TOP N ---
st.header("1. 연도별 직종 구인 규모 TOP N")
c1, c2 = st.columns([1, 3])
with c1:
    years = sorted(df["연도"].unique().tolist())
    sel_year = st.selectbox("연도 선택", years, index=len(years) - 1)
    top_n = st.slider("상위 N개", 5, 20, 10)
by_year = (
    df[df["연도"] == sel_year]
    .groupby("직종_중분류")["구인인원"].sum()
    .sort_values(ascending=False)
    .head(top_n)
    .reset_index()
)
fig1 = px.bar(by_year, x="구인인원", y="직종_중분류", orientation="h",
              title=f"{sel_year}년 구인 규모 상위 {top_n}개 직종")
fig1.update_layout(yaxis={"categoryorder": "total ascending"})
with c2:
    st.plotly_chart(fig1, use_container_width=True)
st.caption("💡 인사이트: 연도별로 꾸준히 상위에 드는 직종이 경기 변동에 강한 안정적 수요를 가진다. 2023→2025 연속 TOP 5에 든 직종을 취업 1순위 목표로 삼아라.")

# --- 그래프 2: 월별 구인 추이 ---
st.header("2. 주요 직종 구인 인원 월별 추이")
top5 = df.groupby("직종_중분류")["구인인원"].sum().nlargest(5).index.tolist()
selected = st.multiselect("직종 선택", df["직종_중분류"].unique().tolist(), default=top5)
if selected:
    trend = df[df["직종_중분류"].isin(selected)].groupby(["기간", "직종_중분류"])["구인인원"].sum().reset_index()
    fig2 = px.line(trend, x="기간", y="구인인원", color="직종_중분류",
                   title="월별 구인인원 추이")
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("💡 인사이트: 구인이 급증하는 시기(보통 3~4월, 9~10월)에 맞춰 지원서를 준비하면 경쟁이 가장 낮은 시점에 지원할 수 있다. 내가 목표하는 직종의 피크 시즌을 확인하라.")

# --- 그래프 3: 연도 × 직종 구인 히트맵 ---
st.header("3. 연도별 직종 구인 규모 히트맵")
hm_n = st.slider("표시할 직종 수 (전체 기간 구인 합계 기준)", 10, 30, 15, key="hm")

yearly = df.groupby(["연도", "직종_중분류"])["구인인원"].sum().reset_index()
top_cats = (
    yearly.groupby("직종_중분류")["구인인원"].sum()
    .nlargest(hm_n).index
)
pivot = (
    yearly[yearly["직종_중분류"].isin(top_cats)]
    .pivot(index="직종_중분류", columns="연도", values="구인인원")
    .fillna(0)
)
# 행(직종)별 최댓값으로 나눠 0~1 정규화 → 직종 규모 차이 무관하게 추세 비교
pivot_norm = pivot.div(pivot.max(axis=1), axis=0).round(3)
# 2021 대비 2025 증감률로 정렬
years_avail = pivot.columns.tolist()
if 2021 in years_avail and 2025 in years_avail:
    sort_key = (pivot[2025] - pivot[2021]) / pivot[2021].replace(0, pd.NA)
    pivot_norm = pivot_norm.loc[sort_key.sort_values().index]

fig3 = px.imshow(
    pivot_norm,
    color_continuous_scale="RdYlGn",
    aspect="auto",
    title="직종별 연도 구인 규모 (각 직종 최대값 기준 정규화, 1=최대)",
    text_auto=".2f",
)
fig3.update_layout(
    xaxis_title="연도",
    yaxis_title="",
    coloraxis_colorbar_title="상대값",
    height=max(400, hm_n * 30),
)
st.plotly_chart(fig3, use_container_width=True)
st.caption("💡 인사이트: 2021→2025로 갈수록 색이 진해지는(초록) 직종이 성장 직종이다. 반대로 색이 옅어지는(빨강) 직종은 구인이 줄고 있어 장기 커리어로는 불리하다 — 10년 뒤를 보고 직종을 고른다면 초록 직종에 집중하라.")

# --- 그래프 4: 취업 경쟁률 ---
st.header("4. 직종별 평균 취업 경쟁률 (구직건수 / 구인인원)")
comp = df.groupby("직종_중분류")["경쟁률"].mean().sort_values(ascending=False).head(15).reset_index()
fig4 = px.bar(comp, x="경쟁률", y="직종_중분류", orientation="h",
              title="취업 경쟁률 상위 15개 직종")
fig4.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig4, use_container_width=True)
st.caption("💡 인사이트: 경쟁률 5 이상이면 자리 1개에 지원자 5명 이상 — 이 직종을 목표로 한다면 스펙 외 포트폴리오·자격증 차별화가 필수다. 반대로 경쟁률 2 미만 직종은 상대적으로 취업이 쉬운 블루오션이다.")