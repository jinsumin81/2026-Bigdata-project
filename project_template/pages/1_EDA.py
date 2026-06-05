import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
from src.data_loader import load_data, load_filtered, COMPARE_GENRES

st.title("📊 EDA — K-pop 데이터 살펴보기")

df = load_data()
df_f = load_filtered()

# ── 1. 데이터 개요 ──────────────────────────────────────────────────────────
st.header("1. 데이터 개요")
c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 트랙 수", f"{len(df):,}")
c2.metric("장르 수", f"{df['track_genre'].nunique()}")
c3.metric("컬럼 수", f"{df.shape[1]}")
c4.metric("결측 있는 열", f"{int(df.isna().any().sum())}")

st.subheader("미리보기 (상위 20행)")
st.dataframe(df.head(20), use_container_width=True)

# ── 2. 요약 통계 ────────────────────────────────────────────────────────────
st.header("2. 오디오 특성 요약 통계")
audio_cols = [
    "popularity", "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness", "loudness", "tempo",
]
st.dataframe(df[audio_cols].describe().T.round(3), use_container_width=True)

# ── 3. 결측치 ───────────────────────────────────────────────────────────────
st.header("3. 결측치 확인")
na = df.isna().sum()
na = na[na > 0].sort_values(ascending=False)
if len(na) == 0:
    st.success("결측치 없음 ✅")
else:
    st.bar_chart(na)

# ── 4. Popularity 분포 ──────────────────────────────────────────────────────
st.header("4. Popularity 분포")
col1, col2 = st.columns(2)
with col1:
    fig_pop = px.histogram(
        df, x="popularity", nbins=50,
        title="전체 트랙 Popularity 분포",
        color_discrete_sequence=["#636EFA"],
    )
    st.plotly_chart(fig_pop, use_container_width=True)
with col2:
    zero_pct = (df["popularity"] == 0).mean() * 100
    st.metric("Popularity = 0 비율", f"{zero_pct:.1f}%")
    st.info("Popularity = 0인 트랙은 사실상 미노출/숨겨진 곡입니다. 모델 학습 전 제거를 권장합니다.")
    fig_box = px.box(
        df_f, x="track_genre", y="popularity",
        title="비교 장르별 Popularity 분포", color="track_genre",
        category_orders={"track_genre": COMPARE_GENRES},
    )
    st.plotly_chart(fig_box, use_container_width=True)

# ── 5. 장르별 트랙 수 ───────────────────────────────────────────────────────
st.header("5. 장르별 트랙 수 (비교 대상 6개 장르)")
genre_cnt = df_f["track_genre"].value_counts().reset_index()
genre_cnt.columns = ["장르", "트랙 수"]
fig_genre = px.bar(
    genre_cnt, x="장르", y="트랙 수", color="장르",
    title="장르별 트랙 수", text_auto=True,
)
st.plotly_chart(fig_genre, use_container_width=True)

# ── 6. K-pop vs 글로벌 평균 ─────────────────────────────────────────────────
st.header("6. K-pop vs 글로벌 평균 비교")
kpop = df[df["track_genre"] == "k-pop"]
compare_cols = ["danceability", "energy", "valence", "acousticness", "speechiness"]
compare_df = pd.DataFrame({
    "K-pop 평균": kpop[compare_cols].mean(),
    "전체 평균":  df[compare_cols].mean(),
}).round(3)
st.dataframe(compare_df, use_container_width=True)
st.info(
    f"K-pop 트랙 수: {len(kpop):,}개 / 전체 {len(df):,}개 "
    f"({len(kpop)/len(df)*100:.1f}%)"
)

# ── 7. 주요 발견 ────────────────────────────────────────────────────────────
st.header("7. EDA 주요 발견")
st.info("""
- K-pop은 전체 데이터의 약 1%로 샘플 수가 적어 통계 해석 시 신뢰구간을 함께 고려해야 합니다.
- Popularity = 0인 트랙이 상당 비율 존재하므로 모델 학습 전 필터링이 필요합니다.
- K-pop은 danceability·energy가 높고 acousticness가 낮아 전자음악 중심 구성입니다.
- 비교 대상 6개 장르의 트랙 수는 비슷한 수준으로 공정한 비교가 가능합니다.
""")
