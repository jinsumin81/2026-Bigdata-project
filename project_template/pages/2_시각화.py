import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Windows 한글 폰트 (맑은 고딕)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
from src.data_loader import load_data, load_filtered, COMPARE_GENRES, RADAR_FEATURES

st.title("📈 장르 비교 시각화")

df = load_data()
df_f = load_filtered()

# ── 1. 레이더 차트 ──────────────────────────────────────────────────────────
st.header("1. 장르별 오디오 특성 레이더 차트")
genre_avg = df_f.groupby("track_genre")[RADAR_FEATURES].mean()
fig_radar = go.Figure()
for genre in COMPARE_GENRES:
    if genre not in genre_avg.index:
        continue
    vals = genre_avg.loc[genre, RADAR_FEATURES].tolist()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=RADAR_FEATURES + [RADAR_FEATURES[0]],
        name=genre,
        fill="toself",
        opacity=0.45,
    ))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    title="장르별 평균 오디오 특성 비교",
    height=520,
)
st.plotly_chart(fig_radar, use_container_width=True)
st.caption("K-pop은 danceability·energy가 높고 acousticness가 낮아 전자음악 중심 구성임을 확인할 수 있습니다.")

# ── 2. 상관관계 히트맵 ──────────────────────────────────────────────────────
st.header("2. 고인기 트랙 오디오 특성 상관관계 히트맵")
heat_cols = [
    "popularity", "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness", "loudness", "tempo",
]
high_pop = df[df["popularity"] >= df["popularity"].quantile(0.8)]
fig_heat, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(
    high_pop[heat_cols].corr().round(2),
    annot=True, cmap="coolwarm", fmt=".2f",
    ax=ax, linewidths=0.5,
)
ax.set_title("고인기 트랙(상위 20%) 오디오 특성 상관관계")
st.pyplot(fig_heat)
st.caption("loudness·energy와 popularity 간 양의 상관, acousticness·instrumentalness 간 음의 상관이 뚜렷합니다.")

# ── 3. 박스플롯 ─────────────────────────────────────────────────────────────
st.header("3. 장르별 Popularity 분포 (박스플롯)")
fig_box = px.box(
    df_f, x="track_genre", y="popularity",
    color="track_genre",
    category_orders={"track_genre": COMPARE_GENRES},
    title="장르별 Popularity 분포",
    labels={"track_genre": "장르", "popularity": "인기도"},
)
st.plotly_chart(fig_box, use_container_width=True)
st.caption("K-pop의 Spotify 내 인기도 분포를 주요 글로벌 장르와 비교합니다.")

# ── 4. 산점도 ───────────────────────────────────────────────────────────────
st.header("4. 오디오 특성 vs Popularity 산점도")
c1, c2 = st.columns(2)
x_feat    = c1.selectbox("X축 특성", RADAR_FEATURES, index=0)
genre_sel = c2.multiselect("장르 선택", COMPARE_GENRES, default=["k-pop", "pop"])
df_sel = df_f[df_f["track_genre"].isin(genre_sel)] if genre_sel else df_f
fig_sc = px.scatter(
    df_sel, x=x_feat, y="popularity",
    color="track_genre", opacity=0.4,
    trendline="ols",
    title=f"{x_feat} vs Popularity",
    labels={"track_genre": "장르"},
)
st.plotly_chart(fig_sc, use_container_width=True)

# ── 5. 바이올린 플롯 ────────────────────────────────────────────────────────
st.header("5. K-pop vs Pop 주요 특성 분포 비교 (바이올린 플롯)")
kpop_pop = df_f[df_f["track_genre"].isin(["k-pop", "pop"])]
feat_v = st.selectbox(
    "비교 특성 선택",
    ["danceability", "energy", "valence", "speechiness", "acousticness"],
    index=0,
)
fig_v, ax_v = plt.subplots(figsize=(8, 5))
sns.violinplot(
    data=kpop_pop, x="track_genre", y=feat_v,
    palette={"k-pop": "#FF6B9D", "pop": "#4ECDC4"},
    ax=ax_v,
)
ax_v.set_title(f"K-pop vs Pop: {feat_v} 분포 비교")
ax_v.set_xlabel("장르")
st.pyplot(fig_v)

# ── 6. 장르별 평균 인기도 순위 ─────────────────────────────────────────────
st.header("6. 장르별 평균 Popularity 순위")
avg_pop = (
    df_f.groupby("track_genre")["popularity"]
    .mean()
    .sort_values(ascending=False)
    .reset_index()
)
avg_pop.columns = ["장르", "평균 인기도"]
fig_bar = px.bar(
    avg_pop, x="장르", y="평균 인기도", color="장르",
    text_auto=".1f",
    title="장르별 평균 Popularity 순위",
    category_orders={"장르": avg_pop["장르"].tolist()},
)
st.plotly_chart(fig_bar, use_container_width=True)
st.caption("K-pop이 글로벌 주요 장르 대비 Spotify 인기도에서 어느 위치에 있는지 확인합니다.")

