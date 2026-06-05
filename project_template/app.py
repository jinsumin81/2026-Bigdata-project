import streamlit as st

st.set_page_config(
    page_title="K-pop 글로벌 경쟁력 분석",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

eda     = st.Page("pages/1_EDA.py",       title="EDA",            icon="📊", default=True)
viz     = st.Page("pages/2_시각화.py",    title="장르 비교 시각화", icon="📈")
service = st.Page("pages/3_모델_서비스.py", title="인기도 예측",   icon="🤖")

pg = st.navigation({"K-pop 분석 프로젝트": [eda, viz, service]})

st.sidebar.markdown("### 🎵 K-pop 글로벌 경쟁력 분석")
st.sidebar.caption("Spotify 오디오 특성 기반 EDA & 인기도 예측")
st.sidebar.markdown("---")
st.sidebar.caption("진수민 / 20241479")

pg.run()
