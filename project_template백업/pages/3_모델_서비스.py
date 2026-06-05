import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from src.data_loader import load_data, RADAR_FEATURES
from src.features import clean, AUDIO_FEATURES

st.title("🤖 K-pop 인기도 예측 서비스")
st.caption("2022년 Spotify 데이터 기반 오디오 특성 → popularity 예측 모델 (2022년 글로벌 기준)")


@st.cache_resource
def train_models():
    df = load_data()
    df_clean = clean(df)

    X = df_clean[AUDIO_FEATURES].copy()
    y = df_clean["popularity"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    Xtr, Xte, ytr, yte = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    # 베이스라인: Linear Regression
    lr = LinearRegression()
    lr.fit(Xtr, ytr)
    lr_pred = lr.predict(Xte)

    # 메인 모델: Random Forest
    rf = RandomForestRegressor(
        n_estimators=200, max_depth=10, random_state=42, n_jobs=-1
    )
    rf.fit(Xtr, ytr)
    rf_pred = rf.predict(Xte)

    # 레이더 비교용 기준 평균
    kpop_mask = df_clean["track_genre"] == "k-pop"
    top20_mask = df_clean["popularity"] >= df_clean["popularity"].quantile(0.8)
    kpop_avg  = df_clean.loc[kpop_mask,  RADAR_FEATURES].mean()
    top20_avg = df_clean.loc[top20_mask, RADAR_FEATURES].mean()

    return {
        "scaler": scaler,
        "lr": lr,
        "rf": rf,
        "metrics": {
            "Linear Regression (베이스라인)": {
                "RMSE": mean_squared_error(yte, lr_pred) ** 0.5,
                "MAE":  mean_absolute_error(yte, lr_pred),
                "R²":   r2_score(yte, lr_pred),
            },
            "Random Forest": {
                "RMSE": mean_squared_error(yte, rf_pred) ** 0.5,
                "MAE":  mean_absolute_error(yte, rf_pred),
                "R²":   r2_score(yte, rf_pred),
            },
        },
        "feat_importance": pd.Series(
            rf.feature_importances_, index=AUDIO_FEATURES
        ).sort_values(ascending=False),
        "kpop_avg":  kpop_avg,
        "top20_avg": top20_avg,
        "pop_quantiles": df_clean["popularity"].quantile([0.2, 0.4, 0.6, 0.8]).to_dict(),
    }


with st.spinner("모델 학습 중... (최초 1회만 실행됩니다)"):
    result = train_models()

# ── 1. 모델 성능 비교 ───────────────────────────────────────────────────────
st.header("1. 모델 성능 비교")
metrics_df = pd.DataFrame(result["metrics"]).T.round(3)
st.dataframe(metrics_df, use_container_width=True)
st.info(
    "**해석:** RMSE·MAE는 낮을수록, R²는 1에 가까울수록 좋은 모델입니다. "
    "음악 인기도는 마케팅·아티스트 인지도 등 외부 요인의 영향이 크기 때문에 "
    "R²가 낮게 나오는 것은 예상된 결과입니다. '완벽한 예측'보다 '트렌드 파악'에 집중합니다."
)

# ── 2. Feature Importance ───────────────────────────────────────────────────
st.header("2. 인기도에 영향을 미치는 오디오 특성 (Random Forest)")
fi = result["feat_importance"].reset_index()
fi.columns = ["특성", "중요도"]
fig_fi = px.bar(
    fi, x="특성", y="중요도", color="중요도",
    color_continuous_scale="Blues",
    title="Feature Importance (Random Forest)",
)
st.plotly_chart(fig_fi, use_container_width=True)

# ── 3. 예측 서비스 ──────────────────────────────────────────────────────────
st.header("3. 나의 곡 인기도 예측해보기")
st.caption("슬라이더로 오디오 특성 값을 조절하면 예상 인기도를 예측합니다.")

col1, col2 = st.columns(2)
with col1:
    danceability     = st.slider("danceability  (춤추기 적합한 정도)", 0.0, 1.0, 0.70, 0.01)
    energy           = st.slider("energy        (강렬함·활동성)",        0.0, 1.0, 0.80, 0.01)
    valence          = st.slider("valence       (긍정적 감정)",           0.0, 1.0, 0.60, 0.01)
    acousticness     = st.slider("acousticness  (어쿠스틱 비율)",         0.0, 1.0, 0.05, 0.01)
    speechiness      = st.slider("speechiness   (음성/랩 비율)",          0.0, 1.0, 0.10, 0.01)
    instrumentalness = st.slider("instrumentalness (연주곡 비율)",        0.0, 1.0, 0.00, 0.01)
with col2:
    liveness    = st.slider("liveness  (라이브 여부)",                    0.0, 1.0, 0.10, 0.01)
    loudness    = st.slider("loudness  (음량, dB)",                       -60.0, 0.0, -5.0, 0.1)
    tempo       = st.slider("tempo     (BPM)",                            50.0, 220.0, 120.0, 1.0)
    duration_ms = st.slider("duration  (곡 길이, ms)",                    60000, 600000, 210000, 10000)
    key         = st.slider("key       (음악 키  C=0 ~ B=11)",            0, 11, 1)
    mode        = st.selectbox(
        "mode", [1, 0],
        format_func=lambda x: "장조 (Major)" if x == 1 else "단조 (Minor)",
    )

if st.button("🎵 인기도 예측하기", type="primary"):
    input_vals = {
        "danceability":     danceability,
        "energy":           energy,
        "valence":          valence,
        "acousticness":     acousticness,
        "instrumentalness": instrumentalness,
        "liveness":         liveness,
        "speechiness":      speechiness,
        "loudness":         loudness,
        "tempo":            tempo,
        "duration_ms":      duration_ms,
        "key":              key,
        "mode":             mode,
    }
    input_df = pd.DataFrame([input_vals])[AUDIO_FEATURES]
    scaled   = result["scaler"].transform(input_df)
    pred     = float(result["rf"].predict(scaled)[0])
    pred     = max(0.0, min(100.0, pred))

    q = result["pop_quantiles"]
    if pred >= q[0.8]:
        pct_label = "상위 20%"
    elif pred >= q[0.6]:
        pct_label = "상위 40%"
    elif pred >= q[0.4]:
        pct_label = "상위 60%"
    else:
        pct_label = "하위 40%"

    st.success(f"### 예상 인기도: **{pred:.1f} / 100**")
    st.write(
        f"2022년 글로벌 Spotify 기준, 이 곡은 **{pct_label}** 수준의 오디오 특성을 가지고 있습니다."
    )
    st.warning(
        "⚠️ 이 예측은 2022년 데이터 기반입니다. "
        "실제 인기도는 마케팅·아티스트 인지도·발매 시기 등 외부 요인에 크게 좌우됩니다."
    )

    # 레이더 차트 3-way 비교
    st.subheader("오디오 특성 비교 (레이더 차트)")
    input_radar = [input_vals[f] for f in RADAR_FEATURES]
    kpop_radar  = result["kpop_avg"][RADAR_FEATURES].tolist()
    top20_radar = result["top20_avg"][RADAR_FEATURES].tolist()
    labels = RADAR_FEATURES + [RADAR_FEATURES[0]]

    fig_r = go.Figure()
    fig_r.add_trace(go.Scatterpolar(
        r=input_radar + [input_radar[0]], theta=labels,
        name="입력 곡", fill="toself", line_color="#FF6B9D",
    ))
    fig_r.add_trace(go.Scatterpolar(
        r=kpop_radar + [kpop_radar[0]], theta=labels,
        name="K-pop 평균", fill="toself", opacity=0.4, line_color="#4ECDC4",
    ))
    fig_r.add_trace(go.Scatterpolar(
        r=top20_radar + [top20_radar[0]], theta=labels,
        name="글로벌 인기 상위 20%", fill="toself", opacity=0.4, line_color="#FFE66D",
    ))
    fig_r.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="입력 곡 vs K-pop 평균 vs 글로벌 인기 상위 20%",
        height=520,
    )
    st.plotly_chart(fig_r, use_container_width=True)
