import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from src.data_loader import load_data, load_filtered, RADAR_FEATURES
from src.features import clean, AUDIO_FEATURES

st.title("K-pop 히트곡 제작 가이드")
st.caption("오디오 특성을 조절하면 예상 인기도와 고인기 K-pop 황금비율을 비교해드립니다")

@st.cache_resource
def train_models():
    df = load_data()
    df_clean = clean(df)
    X = df_clean[AUDIO_FEATURES].copy()
    y = df_clean["popularity"]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    rf = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    metrics = {}
    for name, model in [("Linear Regression", lr), ("Random Forest", rf)]:
        y_pred = model.predict(X_test)
        metrics[name] = {
            "RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
            "MAE":  mean_absolute_error(y_test, y_pred),
            "R2":   r2_score(y_test, y_pred),
        }
    df_filtered = load_filtered()
    kpop_df = df_filtered[df_filtered["track_genre"] == "k-pop"]
    kpop_avg = kpop_df[RADAR_FEATURES].mean()
    threshold = kpop_df["popularity"].quantile(0.8)
    top20_avg = kpop_df[kpop_df["popularity"] >= threshold][RADAR_FEATURES].mean()
    importance = pd.Series(rf.feature_importances_, index=AUDIO_FEATURES).sort_values(ascending=False)
    return lr, rf, scaler, metrics, kpop_avg, top20_avg, importance

lr, rf, scaler, metrics, kpop_avg, top20_avg, importance = train_models()

FEATURE_CONFIG = {
    "danceability":     {"label": "댄서빌리티 (리듬감)",    "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.7},
    "energy":           {"label": "에너지 (강렬함)",         "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.8},
    "valence":          {"label": "발런스 (긍정적 감정)",    "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.5},
    "acousticness":     {"label": "어쿠스틱 비율",           "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.1},
    "instrumentalness": {"label": "연주 비율 (보컬 없음)",   "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.0},
    "liveness":         {"label": "라이브 느낌",             "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.15},
    "speechiness":      {"label": "스피치 비율 (랩/말)",     "min": 0.0,   "max": 1.0,    "step": 0.01, "default": 0.1},
    "loudness":         {"label": "음량 (dB)",               "min": -60.0, "max": 0.0,    "step": 0.5,  "default": -5.0},
    "tempo":            {"label": "템포 (BPM)",              "min": 60.0,  "max": 200.0,  "step": 1.0,  "default": 120.0},
    "duration_ms":      {"label": "곡 길이 (ms)",            "min": 60000, "max": 600000, "step": 1000, "default": 200000},
    "key":              {"label": "음악 키 (0=C 11=B)",      "min": 0,     "max": 11,     "step": 1,    "default": 5},
    "mode":             {"label": "장/단조 (1=장조 0=단조)", "min": 0,     "max": 1,      "step": 1,    "default": 1},
}

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.subheader("내 곡 오디오 특성 설정")
    st.caption("슬라이더로 만들고 싶은 곡의 특성을 입력하세요")
    user_vals = {}
    for feat, cfg in FEATURE_CONFIG.items():
        user_vals[feat] = st.slider(
            cfg["label"],
            min_value=cfg["min"],
            max_value=cfg["max"],
            value=cfg["default"],
            step=cfg["step"],
            key=feat,
        )
    predict_btn = st.button("분석하기", type="primary", use_container_width=True)

with col_right:
    if not predict_btn:
        st.info("왼쪽 슬라이더로 특성을 설정한 후 분석하기 버튼을 누르세요.")
        st.subheader("모델 성능 요약")
        metrics_df = pd.DataFrame(metrics).T.round(3)
        st.dataframe(metrics_df, use_container_width=True)
        st.subheader("인기도에 영향을 미치는 특성 (RF Feature Importance)")
        fig_imp = px.bar(
            x=importance.values, y=importance.index, orientation="h",
            labels={"x": "중요도", "y": "특성"},
            color=importance.values, color_continuous_scale="Blues",
        )
        fig_imp.update_layout(height=400, showlegend=False, coloraxis_showscale=False,
                              yaxis={"autorange": "reversed"}, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_imp, use_container_width=True)
    else:
        X_user = np.array([[user_vals[f] for f in AUDIO_FEATURES]])
        X_user_scaled = scaler.transform(X_user)
        pred_lr = float(lr.predict(X_user_scaled)[0])
        pred_rf = float(rf.predict(X_user_scaled)[0])
        pred_rf = max(0, min(100, pred_rf))
        pred_lr = max(0, min(100, pred_lr))
        df_all = clean(load_data())
        percentile = (df_all["popularity"] < pred_rf).mean() * 100

        st.subheader("예측 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("Random Forest 예측", f"{pred_rf:.1f} / 100")
        c2.metric("Linear 예측 (베이스라인)", f"{pred_lr:.1f} / 100")
        c3.metric("상위 몇 %", f"상위 {100 - percentile:.0f}%")
        st.caption("2022년 글로벌 기준 예측값입니다. 마케팅·발매 시기 등 외부 요인은 포함되지 않습니다.")

        st.subheader("오디오 특성 비교 레이더")
        user_radar  = [user_vals[f] for f in RADAR_FEATURES]
        kpop_radar  = [kpop_avg[f]  for f in RADAR_FEATURES]
        top20_radar = [top20_avg[f] for f in RADAR_FEATURES]
        labels = RADAR_FEATURES + [RADAR_FEATURES[0]]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=user_radar+[user_radar[0]],   theta=labels, fill="toself", name="내 곡 설정",           line_color="#EF553B", opacity=0.7))
        fig_radar.add_trace(go.Scatterpolar(r=kpop_radar+[kpop_radar[0]],   theta=labels, fill="toself", name="K-pop 전체 평균",      line_color="#636EFA", opacity=0.5))
        fig_radar.add_trace(go.Scatterpolar(r=top20_radar+[top20_radar[0]], theta=labels, fill="toself", name="고인기 K-pop 상위 20%", line_color="#00CC96", opacity=0.5))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])),
                                height=420, legend=dict(orientation="h", y=-0.15), margin=dict(l=20,r=20,t=20,b=60))
        st.plotly_chart(fig_radar, use_container_width=True)

        st.subheader("히트곡에 가까워지는 제안")
        st.caption("고인기 K-pop 상위 20% 평균과의 차이 기준")
        suggestions = []
        for feat in RADAR_FEATURES:
            diff = top20_avg[feat] - user_vals[feat]
            feat_label = FEATURE_CONFIG[feat]["label"]
            if abs(diff) > 0.05:
                direction = "올리세요" if diff > 0 else "내리세요"
                arrow = "up" if diff > 0 else "down"
                suggestions.append({"특성": feat_label, "내 설정": round(user_vals[feat],3),
                                     "고인기 평균": round(top20_avg[feat],3), "차이": round(diff,3),
                                     "제안": f"[{arrow}] {direction} ({abs(diff):.2f})"})
        if suggestions:
            sug_df = pd.DataFrame(suggestions).sort_values("차이", key=abs, ascending=False)
            st.dataframe(sug_df, use_container_width=True, hide_index=True)
        else:
            st.success("고인기 K-pop 황금비율과 거의 일치합니다!")

        with st.expander("어떤 특성이 인기도에 가장 영향을 미치나요?"):
            fig_imp2 = px.bar(x=importance.values, y=importance.index, orientation="h",
                              labels={"x": "중요도", "y": "특성"}, color=importance.values, color_continuous_scale="Blues")
            fig_imp2.update_layout(height=380, showlegend=False, coloraxis_showscale=False,
                                   yaxis={"autorange": "reversed"}, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig_imp2, use_container_width=True)
