import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd
from src.data_loader import load_data
from src.features import clean, add_features

st.title("💼 직종 추천 서비스")
st.write("전공과 관심 분야를 선택하면, 최근 데이터 기반으로 유망 직종을 추천해 드립니다.")

df = add_features(clean(load_data()))

# 전공 → 직종 키워드 매핑
MAJOR_TO_KEYWORDS = {
    "IT·컴퓨터·소프트웨어": ["정보통신", "전기·전자"],
    "경영·경제·회계":       ["경영", "회계", "사무", "금융", "보험", "영업"],
    "디자인·예술·미디어":   ["문화", "예술", "디자인", "방송"],
    "기계·전기·전자":       ["기계", "전기", "전자", "재료"],
    "건축·토목·환경":       ["건설", "환경"],
    "보건·의료·간호":       ["보건", "의료"],
    "사회복지·상담":        ["사회복지", "종교"],
    "교육·사범":            ["교육", "자연과학"],
    "식품·조리·영양":       ["식품", "음식", "조리"],
    "법학·경찰·행정":       ["법률", "경찰", "소방"],
    "농림·수산·환경":       ["농림", "어업"],
}

all_categories = sorted(df["직종_중분류"].unique().tolist())

# --- 입력 ---
st.header("1. 정보 입력")
c1, c2 = st.columns([1, 2])
with c1:
    major = st.selectbox("학과(전공) 선택", list(MAJOR_TO_KEYWORDS.keys()))
with c2:
    keywords = MAJOR_TO_KEYWORDS.get(major, [])
    default_cats = [c for c in all_categories if any(kw in str(c) for kw in keywords)]
    selected_cats = st.multiselect(
        "관심 직종 중분류 선택 (자동 추천 + 직접 추가 가능)",
        options=all_categories,
        default=default_cats[:5],
    )

if not selected_cats:
    st.warning("직종 중분류를 하나 이상 선택해 주세요.")
    st.stop()

# --- 처리: 최근 12개월 기준 ---
st.header("2. 추천 결과")
recent_date = df["기간"].max()
start_date  = recent_date - pd.DateOffset(months=11)
prev_start  = start_date - pd.DateOffset(months=12)
prev_end    = start_date - pd.DateOffset(months=1)

df_filtered = df[df["직종_중분류"].isin(selected_cats)]

recent = df_filtered[df_filtered["기간"] >= start_date]
prev   = df_filtered[(df_filtered["기간"] >= prev_start) & (df_filtered["기간"] <= prev_end)]

recent_agg = recent.groupby("직종_중분류").agg(
    구인인원=("구인인원", "sum"),
    구직건수=("구직건수", "sum"),
    취업건수=("취업건수", "sum"),
).reset_index()
prev_agg = prev.groupby("직종_중분류")["구인인원"].sum().rename("전년구인")

summary = recent_agg.merge(prev_agg, on="직종_중분류", how="left")
summary["성장률(%)"] = ((summary["구인인원"] - summary["전년구인"]) / summary["전년구인"].replace(0, pd.NA) * 100).round(1)
summary["경쟁률"]   = (summary["구직건수"] / summary["구인인원"].replace(0, pd.NA)).round(2)
summary["취업률(%)"] = (summary["취업건수"] / summary["구직건수"].replace(0, pd.NA) * 100).round(1)

top5 = summary.sort_values("성장률(%)", ascending=False).head(5).reset_index(drop=True)

# 추천 카드
cols = st.columns(min(len(top5), 5))
for i, row in top5.iterrows():
    with cols[i]:
        st.metric(f"#{i+1} {row['직종_중분류'][:12]}", f"구인 {int(row['구인인원']):,}명")
        st.caption(f"성장률 {row['성장률(%)']:+.1f}% | 경쟁률 {row['경쟁률']:.2f} | 취업률 {row['취업률(%)']:.1f}%")

st.dataframe(
    top5[["직종_중분류", "구인인원", "성장률(%)", "경쟁률", "취업률(%)"]],
    use_container_width=True,
)

# --- 시각화 1: 구인 추이 ---
st.header("3. 선택 직종 구인 추이 (월별)")
trend = df_filtered.groupby(["기간", "직종_중분류"])["구인인원"].sum().reset_index()
fig1 = px.line(trend, x="기간", y="구인인원", color="직종_중분류",
               title="선택 직종 월별 구인인원 추이")
st.plotly_chart(fig1, use_container_width=True)

# --- 시각화 2: 경쟁률 비교 ---
st.header("4. 선택 직종 취업 경쟁률 비교")
fig2 = px.bar(
    summary.sort_values("경쟁률"),
    x="경쟁률", y="직종_중분류", orientation="h",
    color="경쟁률", color_continuous_scale="RdYlGn_r",
    title="직종별 취업 경쟁률 (낮을수록 취업 유리)",
)
fig2.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig2, use_container_width=True)