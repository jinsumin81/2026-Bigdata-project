import pandas as pd


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """결측·이상치 정리."""
    df = df.dropna(subset=["기간", "직종_중분류", "직종_소분류"])
    df = df[df["구인인원"] > 0].copy()
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """파생 변수 추가."""
    # 취업연결비율(%) = 취업건수 / 구직건수 × 100
    # 구직건수는 실제 구직자 수가 아닌 구직신청 건수 기준이므로 엄밀한 취업률이 아님
    df["취업연결비율"] = (df["취업건수"] / df["구직건수"].replace(0, pd.NA) * 100).round(1)

    # 경쟁률 = 구직건수 / 구인인원 (높을수록 경쟁 치열)
    df["경쟁률"] = (df["구직건수"] / df["구인인원"].replace(0, pd.NA)).round(2)

    # 연도·월 컬럼 (시계열 분석용)
    df["연도"] = df["기간"].dt.year
    df["월"] = df["기간"].dt.month

    return df