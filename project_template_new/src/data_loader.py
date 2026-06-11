import pandas as pd
import streamlit as st
import warnings

DATA_PATH = "data/직종별_구인구직취업현황(월)_1780678426992.xlsx"


@st.cache_data
def load_data() -> pd.DataFrame:
    """구인구직취업현황 xlsx를 읽어 소분류 단위 DataFrame으로 반환."""
    warnings.filterwarnings("ignore")

    # 상단 13행은 메타/헤더 → skiprows=14로 건너뜀, 컬럼명은 직접 지정
    df = pd.read_excel(
        DATA_PATH,
        header=None,
        skiprows=14,
    )
    df.columns = ["기간", "직종_중분류", "직종_소분류", "구인인원", "구직건수", "취업건수"]

    # 기간·중분류는 병합 셀로 첫 행에만 값 → ffill로 채움
    df["기간"] = df["기간"].ffill()
    df["직종_중분류"] = df["직종_중분류"].ffill()

    # 소분류가 없는 행 = 합계·소계 → 제거
    df = df[df["직종_소분류"].notna()].copy()

    # 기간 컬럼에 "전체"·"합계" 포함 행 제거 (월 소계 잔여 처리)
    df = df[~df["기간"].astype(str).str.contains("전체|합계", na=False)].copy()

    # 숫자 변환
    for col in ["구인인원", "구직건수", "취업건수"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["구인인원", "구직건수", "취업건수"]).reset_index(drop=True)

    # "2018한국고용직업분류_" / "2025한국고용직업분류_" 등 연도 접두사 제거
    for col in ["직종_중분류", "직종_소분류"]:
        df[col] = df[col].astype(str).str.replace(r"^\d{4}[^_]*_", "", regex=True)

    # 기간 → datetime
    df["기간"] = pd.to_datetime(df["기간"], format="%Y년 %m월", errors="coerce")
    df = df.dropna(subset=["기간"]).sort_values("기간").reset_index(drop=True)

    return df