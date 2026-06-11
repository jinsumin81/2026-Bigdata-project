# app.py — 프로젝트 진입점
# 5주차 영화 대시보드와 동일한 멀티페이지 구조(st.Page + st.navigation).
# 실행:  streamlit run app.py
import streamlit as st

st.set_page_config(
    page_title="취업 인기 직종 추천 서비스",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 페이지 정의
eda     = st.Page("pages/1_EDA.py",        title="EDA",      icon="📊", default=True)
viz     = st.Page("pages/2_시각화.py",     title="시각화",    icon="📈")
service = st.Page("pages/3_모델_서비스.py", title="직종 추천", icon="💼")

pg = st.navigation({
    "취업 인기 직종 추천 서비스": [eda, viz, service],
})

# 사이드바
st.sidebar.markdown("### 💼 취업 인기 직종 추천 서비스")
st.sidebar.caption("구인구직 데이터 기반 직종 트렌드 분석")
st.sidebar.markdown("---")
st.sidebar.caption("진수민 / 20241479")

pg.run()
