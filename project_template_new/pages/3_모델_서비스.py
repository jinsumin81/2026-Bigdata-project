import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from src.data_loader import load_data
from src.features import clean, add_features

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
WORKNET_API_KEY = os.getenv("WORKNET_API_KEY", "")

# 사용자 키워드 → 직종명 검색어 확장 사전 (값은 실제 직종 중분류명 포함 단어 기준)
KEYWORD_EXPAND = {
    # IT·개발
    "코딩": ["정보통신"],
    "프로그래밍": ["정보통신"],
    "개발": ["정보통신"],
    "소프트웨어": ["정보통신"],
    "데이터": ["정보통신"],
    "IT": ["정보통신"],
    "컴퓨터": ["정보통신"],
    "인공지능": ["정보통신"],
    "AI": ["정보통신"],
    "파이썬": ["정보통신"],
    "네트워크": ["정보통신"],
    "앱": ["정보통신"],
    "서버": ["정보통신"],
    # 교육
    "교육": ["교육"],
    "가르치": ["교육"],
    "강의": ["교육"],
    "수업": ["교육"],
    "강사": ["교육"],
    "선생": ["교육"],
    "튜터": ["교육"],
    # 경영·사무
    "경영": ["경영"],
    "관리": ["관리"],
    "행정": ["경영"],
    "사무": ["경영"],
    "회계": ["경영", "금융"],
    "마케팅": ["경영", "영업"],
    "기획": ["경영"],
    "인사": ["경영"],
    # 영업·판매
    "영업": ["영업"],
    "판매": ["영업"],
    "세일즈": ["영업"],
    # 보건·의료
    "의료": ["보건"],
    "간호": ["보건"],
    "의사": ["보건"],
    "병원": ["보건"],
    "치료": ["보건"],
    "재활": ["보건"],
    "약사": ["보건"],
    # 사회복지
    "복지": ["사회복지"],
    "봉사": ["사회복지"],
    "상담": ["사회복지"],
    "돌봄": ["돌봄"],
    "간병": ["돌봄"],
    "육아": ["돌봄"],
    # 건설
    "건설": ["건설"],
    "건축": ["건설"],
    "토목": ["건설"],
    # 금융·보험
    "금융": ["금융"],
    "보험": ["금융"],
    "은행": ["금융"],
    "투자": ["금융"],
    "재무": ["금융"],
    # 예술·디자인
    "디자인": ["예술"],
    "그래픽": ["예술"],
    "미술": ["예술"],
    "예술": ["예술"],
    "방송": ["예술"],
    "영상": ["예술"],
    "사진": ["예술"],
    # 음식·식품
    "요리": ["음식"],
    "조리": ["음식"],
    "셰프": ["음식"],
    "식품": ["식품"],
    # 기계·제조
    "기계": ["기계"],
    "제조": ["제조"],
    "생산": ["기계", "제조"],
    "용접": ["금속"],
    "금속": ["금속"],
    # 전기·전자
    "전기": ["전기"],
    "전자": ["전기"],
    "반도체": ["전기"],
    # 운전·물류
    "운전": ["운전"],
    "물류": ["운전"],
    "배송": ["운전"],
    "운송": ["운전"],
    # 농업
    "농업": ["농림"],
    "농사": ["농림"],
    "축산": ["농림"],
    # 미용
    "미용": ["미용"],
    "뷰티": ["미용"],
    "헤어": ["미용"],
    # 관광·숙박
    "관광": ["여행"],
    "여행": ["여행"],
    "호텔": ["여행"],
    "숙박": ["여행"],
    # 법률
    "법": ["법률"],
    "법률": ["법률"],
    "변호": ["법률"],
    # 스포츠
    "스포츠": ["스포츠"],
    "체육": ["스포츠"],
    "운동": ["스포츠"],
    # 화학·환경
    "화학": ["화학"],
    "환경": ["화학"],
    "에너지": ["화학"],
    # 연구·학문
    "연구": ["인문", "자연", "정보통신"],
    "심리": ["인문"],
    "사회과학": ["인문"],
    # 경비·보안
    "경비": ["경호"],
    "보안": ["경호"],
    "경호": ["경호"],
    # 청소·개인서비스
    "청소": ["청소"],
    "세탁": ["청소"],
}

st.title("직종 추천 서비스")

df = add_features(clean(load_data()))
all_categories = sorted(df["직종_중분류"].unique().tolist())

# ── 1. 입력 ─────────────────────────────────────────────────────────────────
st.header("1. 나에 대해 자유롭게 입력해 주세요")
user_input = st.text_area(
    "전공, 관심사, 잘하는 것, 하고 싶은 일 등 자유롭게 작성하세요.",
    placeholder="예) 컴퓨터공학을 전공했고 데이터 분석과 파이썬을 좋아합니다. 사람들과 소통하는 일도 관심 있어요.",
    height=120,
)

if not user_input.strip():
    st.info("위에 내용을 입력하면 추천이 시작됩니다.")
    st.stop()

# ── 2. LLM으로 키워드 추출 (직종 매핑은 하지 않음) ──────────────────────────
st.header("2. 추천 결과")

llm_available = False
extracted_keywords = []

keyword_prompt = f"""다음 사용자 입력에서 직업·직종과 관련된 핵심 키워드만 추출하세요.
전공, 기술, 관심 분야, 업무 유형을 키워드로 뽑아주세요.
쉼표로 구분된 단어 목록만 출력하고, 설명은 하지 마세요.

입력: "{user_input}"
키워드:"""

try:
    import ollama
    with st.spinner("LLM이 키워드를 추출 중..."):
        res = ollama.chat(
            model="gemma3:4b",
            messages=[{"role": "user", "content": keyword_prompt}],
        )
    extracted_keywords = [k.strip() for k in res["message"]["content"].strip().split(",") if k.strip()]
    llm_available = True
except Exception:
    st.warning("LLM(Ollama)을 사용할 수 없습니다. 입력 텍스트에서 직접 키워드를 분리합니다.")
    extracted_keywords = [w for w in user_input.replace(",", " ").replace(".", " ").split() if len(w) >= 2]

if extracted_keywords:
    st.caption(f"분석된 키워드: {', '.join(extracted_keywords)}")

# ── 3. 키워드 사전으로 직종 후보 확정 (LLM 개입 없음) ───────────────────────
def match_categories(keywords, categories):
    expanded = set(keywords)
    for kw in keywords:
        for base, extras in KEYWORD_EXPAND.items():
            if base in kw or kw in base:
                expanded.update(extras)

    matched = [cat for cat in categories if any(term in cat for term in expanded)]

    # 확장으로도 없으면 원래 키워드로 직접 검색
    if not matched:
        matched = [cat for cat in categories if any(kw in cat for kw in keywords)]

    return matched[:8]

mapped_cats = match_categories(extracted_keywords, all_categories)

if not mapped_cats:
    st.error("관련 직종을 찾지 못했습니다. 입력 내용을 좀 더 구체적으로 작성해 주세요.")
    st.stop()

# ── 4. 데이터 조회 및 복합 점수화 ──────────────────────────────────────────
recent_date = df["기간"].max()
start_date  = recent_date - pd.DateOffset(months=11)
prev_start  = start_date - pd.DateOffset(months=12)
prev_end    = start_date - pd.DateOffset(months=1)

df_filtered = df[df["직종_중분류"].isin(mapped_cats)]
recent = df_filtered[df_filtered["기간"] >= start_date]
prev   = df_filtered[(df_filtered["기간"] >= prev_start) & (df_filtered["기간"] <= prev_end)]

recent_agg = recent.groupby("직종_중분류").agg(
    구인인원=("구인인원", "sum"),
    구직건수=("구직건수", "sum"),
    취업건수=("취업건수", "sum"),
).reset_index()
prev_agg = prev.groupby("직종_중분류")["구인인원"].sum().rename("전년구인")

summary = recent_agg.merge(prev_agg, on="직종_중분류", how="left")
summary["성장률(%)"]       = ((summary["구인인원"] - summary["전년구인"]) / summary["전년구인"].replace(0, pd.NA) * 100).round(1)
summary["경쟁률"]          = (summary["구직건수"] / summary["구인인원"].replace(0, pd.NA)).round(2)
summary["취업연결비율(%)"]  = (summary["취업건수"] / summary["구직건수"].replace(0, pd.NA) * 100).round(1)

def normalize(s):
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else pd.Series([0.5] * len(s), index=s.index)

summary["점수"] = (
    normalize(summary["구인인원"]) * 0.35 +
    normalize(summary["성장률(%)"].fillna(0)) * 0.30 +
    (1 - normalize(summary["경쟁률"].fillna(summary["경쟁률"].max()))) * 0.20 +
    normalize(summary["취업연결비율(%)"].fillna(0)) * 0.15
).round(3)

top5 = summary.sort_values("점수", ascending=False).head(5).reset_index(drop=True)

# 추천 카드
cols = st.columns(min(len(top5), 5))
for i, row in top5.iterrows():
    with cols[i]:
        st.metric(f"#{i+1} {row['직종_중분류'][:12]}", f"구인 {int(row['구인인원']):,}명")
        st.caption(f"성장률 {row['성장률(%)']:+.1f}% | 경쟁률 {row['경쟁률']:.2f} | 취업연결비율 {row['취업연결비율(%)']:.1f}%")

st.dataframe(
    top5[["직종_중분류", "구인인원", "성장률(%)", "경쟁률", "취업연결비율(%)", "점수"]],
    use_container_width=True,
)


# ── 5. ML 분류 모델: 직종 성장/감소 예측 (RandomForest) ─────────────────────
st.subheader("직종 성장 예측 모델 (RandomForest 분류)")

@st.cache_data
def train_growth_model(_df):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score

    # 월별 집계 (직종_중분류 × 기간)
    monthly = _df.groupby(["직종_중분류", "기간"]).agg(
        구인합계=("구인인원", "sum"),
        경쟁률평균=("경쟁률", "mean"),
        취업연결평균=("취업연결비율", "mean"),
    ).reset_index()
    monthly["연도"] = monthly["기간"].dt.year
    monthly["월"]   = monthly["기간"].dt.month

    # 전년 동월 구인합계 merge
    prev = monthly[["직종_중분류", "기간", "구인합계"]].copy()
    prev["기간"] = prev["기간"] + pd.DateOffset(years=1)
    prev = prev.rename(columns={"구인합계": "전년구인"})
    data = monthly.merge(prev, on=["직종_중분류", "기간"], how="inner")
    data["성장"] = (data["구인합계"] > data["전년구인"]).astype(int)

    # 피처: 경쟁률, 취업연결비율, 전년구인, 월(계절성)
    X = data[["경쟁률평균", "취업연결평균", "전년구인", "월"]].fillna(0).values
    y = data["성장"].values

    if len(X) < 20:
        return None, None, None, None

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_tr, y_tr)
    y_pred = clf.predict(X_te)

    return clf, accuracy_score(y_te, y_pred), f1_score(y_te, y_pred, zero_division=0), data

try:
    clf, acc, f1_val, model_data = train_growth_model(df)
    if clf is not None:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("모델 정확도 (Accuracy)", f"{acc:.1%}")
        mc2.metric("F1 Score", f"{f1_val:.3f}")
        mc3.metric("학습 샘플 수", f"{len(model_data):,}개 (직종×월)")
        st.caption("💡 인사이트: 월별 데이터(경쟁률·취업연결비율·전년 동월 구인규모·계절성)로 해당 직종의 구인이 전년 동월 대비 늘어날지 줄어들지를 RandomForest로 분류합니다. 테스트셋 20% 기준 정확도와 F1 Score를 평가지표로 사용합니다.")

        st.write("**추천 직종별 성장 예측 결과**")
        recent = df["기간"].max()
        pred_rows = []
        for _, row in top5.iterrows():
            cat = row["직종_중분류"]
            cat_df = df[(df["직종_중분류"] == cat) & (df["기간"] == recent)]
            if cat_df.empty:
                cat_df = df[(df["직종_중분류"] == cat)].sort_values("기간").tail(1)
            prev_df = df[(df["직종_중분류"] == cat) & (df["기간"] == recent - pd.DateOffset(years=1))]
            prev_구인 = float(prev_df["구인인원"].sum()) if not prev_df.empty else 0.0
            feat = [[
                float(cat_df["경쟁률"].mean()),
                float(cat_df["취업연결비율"].mean()),
                prev_구인,
                int(recent.month),
            ]]
            pred = int(clf.predict(feat)[0])
            prob = float(clf.predict_proba(feat)[0][pred])
            pred_rows.append({
                "직종": cat,
                "예측": "📈 성장" if pred == 1 else "📉 감소",
                "신뢰도": f"{prob:.1%}",
            })
        if pred_rows:
            st.dataframe(pd.DataFrame(pred_rows), use_container_width=True, hide_index=True)
    else:
        st.info("데이터가 부족해 모델을 학습하지 못했습니다.")
except Exception as e:
    st.warning(f"모델 학습 오류: {e}")
# ── 6. 워크넷 직업사전 API로 세부 직업명 조회 ──────────────────────────────
def get_specific_jobs(category_name):
    if not WORKNET_API_KEY:
        return []
    try:
        keyword = category_name.replace("관련직", "").replace("전문가", "").strip().split()[0]
        res = requests.get(
            "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo212L01.do",
            params={"authKey": WORKNET_API_KEY, "returnType": "XML",
                    "target": "JOBCD", "srchType": "K", "keyword": keyword},
            timeout=5,
        )
        if res.status_code != 200:
            return []
        root = ET.fromstring(res.text)
        return [item.findtext("jobNm") or "" for item in root.iter("jobList")][:5]
    except Exception:
        return []

specific_jobs = {}
if WORKNET_API_KEY:
    with st.spinner("워크넷 직업사전에서 세부 직업명 조회 중..."):
        for _, row in top5.iterrows():
            jobs = get_specific_jobs(row["직종_중분류"])
            if jobs:
                specific_jobs[row["직종_중분류"]] = jobs

if specific_jobs:
    st.subheader("세부 직업명 (워크넷 직업사전 기준)")
    for cat, jobs in specific_jobs.items():
        st.write(f"**{cat}**: {', '.join(jobs)}")

# ── 7. 시각화 ───────────────────────────────────────────────────────────────
st.header("3. 선택 직종 구인 추이 (월별)")
trend = df_filtered.groupby(["기간", "직종_중분류"])["구인인원"].sum().reset_index()
fig1 = px.line(trend, x="기간", y="구인인원", color="직종_중분류",
               title="관련 직종 월별 구인인원 추이")
st.plotly_chart(fig1, use_container_width=True)
st.caption("💡 인사이트: 최근 3개월간 구인이 증가 추세인 직종이 지금 지원하기 가장 좋은 타이밍이다 — 그래프에서 우상향하는 직종을 1순위 지원 타겟으로 잡아라.")

st.header("4. 직종별 취업 경쟁률 비교")
fig2 = px.bar(
    summary.sort_values("경쟁률"),
    x="경쟁률", y="직종_중분류", orientation="h",
    color="경쟁률", color_continuous_scale="RdYlGn_r",
    title="직종별 취업 경쟁률 (낮을수록 취업 유리)",
)
fig2.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig2, use_container_width=True)
st.caption("💡 인사이트: 같은 추천 직종이라도 경쟁률이 낮은 직종에 먼저 지원하면 합격 확률이 올라간다 — 막대가 짧을수록 자리 대비 경쟁자가 적은 직종이다.")

# ── 8. LLM 최종 리포트 (수치 해석 및 준비 방향만, 직업명 창작 금지) ─────────
st.header("5. AI 분석 리포트")

if llm_available:
    summary_text = "\n".join(
        f"- {row['직종_중분류']}: 구인 {int(row['구인인원']):,}명, 성장률 {row['성장률(%)']:+.1f}%, 경쟁률 {row['경쟁률']:.2f}, 취업연결비율 {row['취업연결비율(%)']:.1f}%"
        for _, row in top5.iterrows()
    )
    jobs_text = "\n".join(
        f"- {cat}: {', '.join(jobs)}" for cat, jobs in specific_jobs.items()
    ) if specific_jobs else "(직업사전 미조회)"

    report_prompt = f"""사용자 정보:
"{user_input}"

워크넷 데이터 분석 결과 (최근 12개월):
{summary_text}

워크넷 직업사전 세부 직업명:
{jobs_text}

위 데이터를 바탕으로 다음 세 가지를 한국어로 서술해 주세요.
반드시 위에 제시된 직업명만 사용하고, 임의로 직업명을 만들지 마세요.
1. 각 직종의 시장 현황 해석 (수치와 함께, 경쟁률·성장률이 무엇을 의미하는지 설명)
2. 사용자 배경에 맞는 직업 추천 (직업사전에 있는 직업명 기준으로만)
3. 추천 직업별 취업 준비 방향 조언
"""
    with st.spinner("AI가 분석 리포트를 작성 중..."):
        try:
            report_res = ollama.chat(
                model="gemma3:4b",
                messages=[{"role": "user", "content": report_prompt}],
            )
            st.markdown(report_res["message"]["content"])
        except Exception as e:
            st.error(f"리포트 생성 중 오류: {e}")
else:
    st.info("Ollama를 설치하고 gemma3:4b 모델을 받으면 AI 분석 리포트가 표시됩니다.")
