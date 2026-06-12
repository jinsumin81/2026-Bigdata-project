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

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
WORKNET_API_KEY = os.getenv("WORKNET_API_KEY", "")

st.title("직종 추천 서비스")

df = add_features(clean(load_data()))
all_categories = sorted(df["직종_중분류"].unique().tolist())

# ── 1. 입력 ──────────────────────────────────────────────────────────────────
st.header("1. 나에 대해 자유롭게 입력해 주세요")
user_input = st.text_area(
    "전공, 관심사, 잘하는 것, 하고 싶은 일 등 자유롭게 작성하세요.",
    placeholder="예) 컴퓨터공학을 전공했고 데이터 분석과 파이썬을 좋아합니다.",
    height=120,
)

if not user_input.strip():
    st.info("위에 내용을 입력하면 추천이 시작됩니다.")
    st.stop()

# ── 캐시 확인 ─────────────────────────────────────────────────────────────────
# 같은 입력이면 재계산 건너뜀 (다운로드 버튼 클릭 등 rerun 대응)
_run_key = user_input.strip()
_cache = st.session_state.get("_cache", {})
_use_cache = _cache.get("run_key") == _run_key

if _use_cache:
    llm_available  = _cache["llm_available"]
    want_keywords  = _cache["want_keywords"]
    avoid_keywords = _cache["avoid_keywords"]
    mapped_cats    = _cache["mapped_cats"]
    unique_jobs    = _cache["unique_jobs"]
    top5           = _cache["top5"]
    summary        = _cache["summary"]
    df_filtered    = _cache["df_filtered"]
    pred_rows      = _cache["pred_rows"]
    clf            = _cache["clf"]
    acc            = _cache["acc"]
    f1_val         = _cache["f1_val"]
    model_data     = _cache["model_data"]
    job_cat_map    = _cache["job_cat_map"]

else:
    # ── COMPUTE: LLM 의도 + 카테고리 분석 ────────────────────────────────────
    llm_available  = False
    want_keywords  = []
    avoid_keywords = []
    mapped_cats    = []
    categories_list = "\n".join(f"- {c}" for c in all_categories)

    intent_prompt = f"""사용자의 전공과 희망 직무를 분석하세요.

사용자 입력: "{user_input}"

아래는 직종 분류 목록 전체입니다:
{categories_list}

규칙:
- want: 워크넷 직업 검색용 1~2단어 짧은 키워드 (긴 직업명은 핵심 단어로 줄이세요)
- avoid: 원하지 않는 업무의 핵심 단어 (없으면 빈 배열)
- categories: 위 직종 분류 목록에서 사용자와 관련 있는 것 최대 4개 (목록에 있는 이름 그대로 복사)

예시1 - AI소프트웨어 전공, 데이터 개발자 희망:
{{"want": ["소프트웨어", "데이터", "개발자"], "avoid": [], "categories": ["정보통신 연구개발직 및 공학기술직"]}}

예시2 - 기계공학과인데 사무직 희망:
{{"want": ["품질관리", "생산관리", "기술영업"], "avoid": ["수리", "정비"], "categories": ["경영·행정·사무직", "영업·판매직"]}}

예시3 - 간호학과인데 행정직 희망:
{{"want": ["의무행정", "병원행정", "의료사무"], "avoid": ["간호", "치료"], "categories": ["보건·의료직", "경영·행정·사무직"]}}

예시4 - 교육학과, 교사·강사 희망:
{{"want": ["교사", "강사", "교육"], "avoid": [], "categories": ["교육직"]}}

주의: categories는 반드시 위 직종 분류 목록에서 정확히 일치하는 이름만 선택하세요.
JSON만 출력:"""

    try:
        import ollama
        import json as _json
        with st.spinner("입력 내용 분석 중..."):
            res = ollama.chat(model="gemma3:4b", messages=[{"role": "user", "content": intent_prompt}])
        raw = res["message"]["content"].strip()
        parsed = _json.loads(raw[raw.find("{"):raw.rfind("}")+1])
        want_keywords  = [k.strip() for k in parsed.get("want", [])  if k.strip()]
        avoid_keywords = [k.strip() for k in parsed.get("avoid", []) if k.strip()]
        mapped_cats    = [c.strip() for c in parsed.get("categories", []) if c.strip() in all_categories]
        llm_available  = True
    except Exception:
        import json as _json
        st.warning("Ollama를 사용할 수 없습니다. 텍스트에서 직접 키워드를 추출합니다.")
        want_keywords = [w for w in user_input.replace(",", " ").replace(".", " ").split() if len(w) >= 2]
        mapped_cats   = [cat for cat in all_categories if any(kw in cat for kw in want_keywords)][:4]

    # ── COMPUTE: 워크넷 API 직업 검색 ────────────────────────────────────────
    def search_worknet_jobs(keyword):
        if not WORKNET_API_KEY:
            return []
        try:
            r = requests.get(
                "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo212L01.do",
                params={"authKey": WORKNET_API_KEY, "returnType": "XML",
                        "target": "JOBCD", "srchType": "K", "keyword": keyword},
                timeout=5,
            )
            if r.status_code != 200:
                return []
            root = ET.fromstring(r.content.decode("utf-8"))
            return [
                {"jobNm": item.findtext("jobNm") or "",
                 "jobClcdNM": item.findtext("jobClcdNM") or "",
                 "jobCd": item.findtext("jobCd") or ""}
                for item in root.iter("jobList") if item.findtext("jobNm")
            ]
        except Exception:
            return []

    def is_avoided(job, avoid_kws):
        target = (job["jobNm"] + job["jobClcdNM"]).lower()
        return any(av.lower() in target for av in avoid_kws)

    found_jobs_dict = {}
    with st.spinner("워크넷 직업사전 검색 중..."):
        for kw in want_keywords:
            for j in search_worknet_jobs(kw):
                if j["jobCd"] not in found_jobs_dict and not is_avoided(j, avoid_keywords):
                    found_jobs_dict[j["jobCd"]] = j
    unique_jobs = list(found_jobs_dict.values())

    # ── COMPUTE: 시장 데이터 집계 ─────────────────────────────────────────────
    top5 = pd.DataFrame()
    summary = pd.DataFrame()
    df_filtered = pd.DataFrame()

    if mapped_cats:
        recent_date = df["기간"].max()
        start_date  = recent_date - pd.DateOffset(months=11)
        prev_start  = start_date - pd.DateOffset(months=12)
        prev_end    = start_date - pd.DateOffset(months=1)

        df_filtered = df[df["직종_중분류"].isin(mapped_cats)]
        recent_df   = df_filtered[df_filtered["기간"] >= start_date]
        prev_df     = df_filtered[(df_filtered["기간"] >= prev_start) & (df_filtered["기간"] <= prev_end)]

        recent_agg = recent_df.groupby("직종_중분류").agg(
            구인인원=("구인인원", "sum"), 구직건수=("구직건수", "sum"), 취업건수=("취업건수", "sum"),
        ).reset_index()
        prev_agg = prev_df.groupby("직종_중분류")["구인인원"].sum().rename("전년구인")
        summary  = recent_agg.merge(prev_agg, on="직종_중분류", how="left")
        summary["성장률(%)"]      = ((summary["구인인원"] - summary["전년구인"]) / summary["전년구인"].replace(0, pd.NA) * 100).round(1)
        summary["경쟁률"]         = (summary["구직건수"] / summary["구인인원"].replace(0, pd.NA)).round(2)
        summary["취업연결비율(%)"] = (summary["취업건수"] / summary["구직건수"].replace(0, pd.NA) * 100).round(1)

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

    # ── COMPUTE: ML 성장 예측 ─────────────────────────────────────────────────
    pred_rows = []
    clf = acc = f1_val = model_data = None

    if not top5.empty:
        @st.cache_data
        def train_growth_model(_df):
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, f1_score
            monthly = _df.groupby(["직종_중분류", "기간"]).agg(
                구인합계=("구인인원", "sum"), 경쟁률평균=("경쟁률", "mean"), 취업연결평균=("취업연결비율", "mean"),
            ).reset_index()
            monthly["월"] = monthly["기간"].dt.month
            prev = monthly[["직종_중분류", "기간", "구인합계"]].copy()
            prev["기간"] = prev["기간"] + pd.DateOffset(years=1)
            prev = prev.rename(columns={"구인합계": "전년구인"})
            data = monthly.merge(prev, on=["직종_중분류", "기간"], how="inner")
            data["성장"] = (data["구인합계"] > data["전년구인"]).astype(int)
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
                recent_date = df["기간"].max()
                for _, row in top5.iterrows():
                    cat    = row["직종_중분류"]
                    cat_df = df[(df["직종_중분류"] == cat) & (df["기간"] == recent_date)]
                    if cat_df.empty:
                        cat_df = df[df["직종_중분류"] == cat].sort_values("기간").tail(1)
                    prev_df2 = df[(df["직종_중분류"] == cat) & (df["기간"] == recent_date - pd.DateOffset(years=1))]
                    prev_구인 = float(prev_df2["구인인원"].sum()) if not prev_df2.empty else 0.0
                    feat = [[float(cat_df["경쟁률"].mean()), float(cat_df["취업연결비율"].mean()), prev_구인, int(recent_date.month)]]
                    pred = int(clf.predict(feat)[0])
                    prob = float(clf.predict_proba(feat)[0][pred])
                    pred_rows.append({
                        "직종": cat, "예측": "성장" if pred == 1 else "감소",
                        "신뢰도": f"{prob:.1%}", "구인인원": int(row["구인인원"]),
                        "성장률(%)": row["성장률(%)"], "경쟁률": row["경쟁률"],
                        "취업연결비율(%)": row["취업연결비율(%)"],
                    })
        except Exception as e:
            st.warning(f"모델 학습 오류: {e}")

    # ── COMPUTE: 직업→카테고리 매핑 ──────────────────────────────────────────
    job_cat_map = {}
    if llm_available and unique_jobs and pred_rows:
        cat_list  = "\n".join(f"- {p['직종']}" for p in pred_rows)
        job_list  = "\n".join(f"- {j['jobNm'].strip()}" for j in unique_jobs[:9])
        mapping_prompt = f"""아래 직업들을 직종 분류 중 가장 관련 있는 하나에 매핑하세요.

직종 분류 목록:
{cat_list}

직업 목록:
{job_list}

각 직업을 위 직종 분류 중 하나에 매핑해서 JSON으로만 출력하세요.
형식: {{"직업명": "직종분류명", ...}}
JSON만 출력:"""
        try:
            with st.spinner("직업-직종 매핑 중..."):
                map_res = ollama.chat(model="gemma3:4b", messages=[{"role": "user", "content": mapping_prompt}])
            raw = map_res["message"]["content"].strip()
            job_cat_map = _json.loads(raw[raw.find("{"):raw.rfind("}")+1])
        except Exception:
            job_cat_map = {}

    # ── 모든 계산 결과 캐시에 저장 ────────────────────────────────────────────
    st.session_state["_cache"] = {
        "run_key": _run_key, "llm_available": llm_available,
        "want_keywords": want_keywords, "avoid_keywords": avoid_keywords,
        "mapped_cats": mapped_cats, "unique_jobs": unique_jobs,
        "top5": top5, "summary": summary, "df_filtered": df_filtered,
        "pred_rows": pred_rows, "clf": clf, "acc": acc,
        "f1_val": f1_val, "model_data": model_data, "job_cat_map": job_cat_map,
    }
    # 새 입력이면 이전 리포트 초기화
    st.session_state.pop("report_text", None)

# ── 캡션 표시 ─────────────────────────────────────────────────────────────────
if want_keywords:
    info = f"검색 키워드: {', '.join(want_keywords)}"
    if avoid_keywords:
        info += f"  |  제외: {', '.join(avoid_keywords)}"
    st.caption(info)
if mapped_cats:
    st.caption(f"분석 직종: {', '.join(mapped_cats)}")

# 다운로드 배너 자리 예약
download_placeholder = st.empty()

# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY PHASE
# ═══════════════════════════════════════════════════════════════════════════════

# ── 2. AI 분석 리포트 ─────────────────────────────────────────────────────────
st.header("2. AI 분석 리포트")

if llm_available:
    def make_stats_line(p):
        return (
            f"[{p['직종']}] - 구인 {p['구인인원']:,}명, "
            f"성장률 {p['성장률(%)']:+.1f}%, 경쟁률 {p['경쟁률']:.2f}, "
            f"취업연결비율 {p['취업연결비율(%)']:.1f}%, "
            f"ML예측: {p['예측']} (신뢰도 {p['신뢰도']})"
        )

    def get_stats_line(job):
        if not pred_rows:
            return "관련 수치를 연동하지 못했습니다"
        matched_cat = job_cat_map.get(job["jobNm"].strip())
        p = next((x for x in pred_rows if x["직종"] == matched_cat), pred_rows[0])
        return make_stats_line(p)

    # 직업명 중복 제거
    seen_names, deduped_jobs = set(), []
    for j in unique_jobs:
        nm = j["jobNm"].strip()
        if nm not in seen_names:
            seen_names.add(nm)
            deduped_jobs.append(j)

    has_jobs = bool(deduped_jobs)

    if has_jobs:
        jobs_section = "\n".join(
            f"- {j['jobNm'].strip()} | 관련수치: {get_stats_line(j)}"
            for j in deduped_jobs
        )
        data_block = f"""[직업별 추천 목록 및 시장 수치 - 워크넷 데이터 + ML 예측]
※ 각 직업 옆 '관련수치'는 해당 직업이 속한 직종 분류의 실제 통계입니다.
{jobs_section}"""
        job_instruction = """추천 직업 TOP 3을 아래 형식으로 작성하세요 (직업 목록에서만 선택, 서로 다른 3개):

### 1. [직업명]

**관련 수치:** (위 목록에서 해당 직업의 관련수치를 그대로 복사)

**추천 이유:** (사용자 배경과의 연관성, 시장 현황 분석을 서술형으로)

**취업 준비 전략:** (구체적인 준비 방법)

---

### 2. [직업명]

**관련 수치:** (위 목록에서 해당 직업의 관련수치를 그대로 복사)

**추천 이유:** (사용자 배경과의 연관성, 시장 현황 분석을 서술형으로)

**취업 준비 전략:** (구체적인 준비 방법)

---

### 3. [직업명]

**관련 수치:** (위 목록에서 해당 직업의 관련수치를 그대로 복사)

**추천 이유:** (사용자 배경과의 연관성, 시장 현황 분석을 서술형으로)

**취업 준비 전략:** (구체적인 준비 방법)"""
    else:
        st.info("워크넷 직업 검색 결과가 없어 직종 분류 시장 데이터 기준으로 분석합니다.")
        cat_stats = "\n".join(make_stats_line(p) for p in pred_rows) if pred_rows else "(시장 데이터 없음)"
        data_block = f"""[직종 분류별 시장 통계 - 워크넷 데이터 + ML 예측]
※ 워크넷 직업 검색 결과가 없어 직종 분류 단위로 분석합니다.
{cat_stats}"""
        job_instruction = """직종 분류별 시장 현황을 바탕으로 사용자에게 적합한 직종 방향을 아래 형식으로 작성하세요:

### 1. [직종 분류명]

**관련 수치:** (위 직종 분류 통계를 그대로 복사)

**추천 이유:** (사용자 배경과의 연관성, 시장 현황 분석을 서술형으로)

**취업 준비 전략:** (구체적인 준비 방법)

---

### 2. [직종 분류명]

**관련 수치:** (위 직종 분류 통계를 그대로 복사)

**추천 이유:** (사용자 배경과의 연관성, 시장 현황 분석을 서술형으로)

**취업 준비 전략:** (구체적인 준비 방법)"""

    # 캐시된 리포트가 있으면 재사용, 없으면 새로 생성
    if st.session_state.get("report_text"):
        st.markdown(st.session_state["report_text"])
        st.caption("⚠️ 본 리포트는 워크넷 공개 데이터를 기반으로 AI가 자동 분석한 결과입니다. 실제 채용 시장과 차이가 있을 수 있으므로 참고용으로만 활용하시기 바랍니다.")
    else:
        report_prompt = f"""사용자 정보: "{user_input}"

{data_block}

위 데이터만 사용해서 한국어로 작성하세요.
절대 지켜야 할 규칙:
- 수치는 위 데이터에 있는 것만 인용하세요. 없는 숫자를 만들거나 추측하지 마세요.
- 관련 수치 항목은 "[직종명] - 구인 XX명, ..." 형식 그대로 복사하세요. [직종명]을 절대 생략하지 마세요.

{job_instruction}
"""
        with st.spinner("AI 리포트 작성 중..."):
            try:
                report_res = ollama.chat(model="gemma3:4b", messages=[{"role": "user", "content": report_prompt}])
                report_text = report_res["message"]["content"]
                st.session_state["report_text"] = report_text
                st.markdown(report_text)
                st.caption("⚠️ 본 리포트는 워크넷 공개 데이터를 기반으로 AI가 자동 분석한 결과입니다. 실제 채용 시장과 차이가 있을 수 있으므로 참고용으로만 활용하시기 바랍니다.")
            except Exception as e:
                st.error(f"리포트 생성 오류: {e}")
else:
    st.info("Ollama를 설치하고 gemma3:4b 모델을 받으면 AI 분석 리포트가 표시됩니다.")

st.divider()

# ── 3. 워크넷 직업 목록 ────────────────────────────────────────────────────────
st.header("3. 워크넷 직업사전 검색 결과")
if unique_jobs:
    cols = st.columns(3)
    for i, job in enumerate(unique_jobs[:9]):
        with cols[i % 3]:
            st.success(f"**{job['jobNm'].strip()}**\n\n{job['jobClcdNM'].strip()}")
elif not WORKNET_API_KEY:
    st.warning("워크넷 API 키가 설정되지 않았습니다.")
else:
    st.warning("관련 직업을 찾지 못했습니다. 키워드를 바꿔서 다시 입력해 보세요.")

# ── 4. 시장 현황 테이블 ────────────────────────────────────────────────────────
if not top5.empty:
    st.header("4. 관련 직종 시장 현황 (워크넷 데이터 기준)")
    cols = st.columns(min(len(top5), 5))
    for i, row in top5.iterrows():
        with cols[i]:
            st.metric(f"#{i+1} {row['직종_중분류'][:12]}", f"구인 {int(row['구인인원']):,}명")
            st.caption(f"성장률 {row['성장률(%)']:+.1f}% | 경쟁률 {row['경쟁률']:.2f} | 취업연결비율 {row['취업연결비율(%)']:.1f}%")
    st.dataframe(
        top5[["직종_중분류", "구인인원", "성장률(%)", "경쟁률", "취업연결비율(%)", "점수"]],
        use_container_width=True,
    )

# ── 5. ML 예측 결과 ────────────────────────────────────────────────────────────
if pred_rows:
    st.header("5. 직종 성장 예측 모델 (RandomForest 분류)")
    if clf is not None and acc is not None:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("모델 정확도 (Accuracy)", f"{acc:.1%}")
        mc2.metric("F1 Score", f"{f1_val:.3f}")
        mc3.metric("학습 샘플 수", f"{len(model_data):,}개 (직종×월)")
    display_df = pd.DataFrame(pred_rows)[["직종", "예측", "신뢰도"]]
    display_df["예측"] = display_df.apply(
        lambda r: "📈 " + r["예측"] if r["예측"] == "성장" else "📉 " + r["예측"], axis=1
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── 6. 차트 ────────────────────────────────────────────────────────────────────
if not df_filtered.empty:
    st.header("6. 선택 직종 구인 추이 (월별)")
    trend = df_filtered.groupby(["기간", "직종_중분류"])["구인인원"].sum().reset_index()
    fig1 = px.line(trend, x="기간", y="구인인원", color="직종_중분류", title="관련 직종 월별 구인인원 추이")
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("💡 최근 3개월간 구인이 증가 추세인 직종이 지금 지원하기 가장 좋은 타이밍입니다.")

if not summary.empty:
    st.header("7. 직종별 취업 경쟁률 비교")
    fig2 = px.bar(
        summary.sort_values("경쟁률"),
        x="경쟁률", y="직종_중분류", orientation="h",
        color="경쟁률", color_continuous_scale="RdYlGn_r",
        title="직종별 취업 경쟁률 (낮을수록 취업 유리)",
    )
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)

# ── 다운로드 배너 ─────────────────────────────────────────────────────────────
if st.session_state.get("report_text"):
    with download_placeholder.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.warning("화면을 나가면 분석 결과가 초기화됩니다. 리포트를 저장하시겠습니까?")
        with col2:
            st.download_button(
                label="📥 예, 다운로드",
                data=st.session_state["report_text"],
                file_name="직종추천_리포트.txt",
                mime="text/plain",
                use_container_width=True,
            )
