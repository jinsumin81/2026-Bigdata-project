import pandas as pd
import streamlit as st

AUDIO_FEATURES = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness", "loudness", "tempo",
    "duration_ms", "key", "mode"
]

RADAR_FEATURES = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness"
]

COMPARE_GENRES = ["k-pop", "pop", "hip-hop", "latin", "r-n-b", "dance"]

# 실제 K-pop/한국 아티스트 화이트리스트
# track_genre == "k-pop" 이지만 힌디·타밀·서양 가수가 섞여 있어서 직접 필터링
KPOP_ARTISTS = {
    # 그룹
    "BTS", "BLACKPINK", "Stray Kids", "TWICE", "SEVENTEEN",
    "TOMORROW X TOGETHER", "ENHYPEN", "ITZY", "aespa",
    "Red Velvet", "MAMAMOO", "(G)I-DLE", "ATEEZ", "PSY",
    "EVERGLOW", "LE SSERAFIM", "EXO", "IVE", "NMIXX", "STAYC",
    "PENTAGON", "Monsta X", "WINNER", "iKON", "BIGBANG",
    "Girls' Generation", "GFRIEND", "EXID", "LOONA", "Dreamcatcher",
    "IZ*ONE", "SECRET NUMBER", "DAVICHI", "OH MY GIRL", "Kep1er",
    "Weeekly", "MOMOLAND", "ONEUS", "I-LAND", "Brave Girls",
    "NCT 127", "NCT DREAM", "NCT U", "NCT", "WayV",
    # 솔로이스트
    "IU", "JEON SOMI", "TAEYEON", "SUNMI", "HyunA", "CL",
    "ZICO", "SOYOU", "LeeHi", "Younha", "K.Will", "Suzy",
    "AILEE", "HEIZE", "BIBI", "SURAN", "Gummy", "Yoon Mirae",
    "Stella Jang", "Seori", "AleXa", "KIMSEJEONG", "Hwa Sa",
    "Jay Park", "Jessi", "Sam Kim", "Sunwoojunga", "DeVita",
    "Punch", "Toaka", "SUVI",
    # 멤버 솔로
    "j-hope", "ROSÉ", "LISA", "JENNIE", "RM", "SUGA", "JIN",
    "KAI", "CHEN", "D.O.", "CHANYEOL", "BAEKHYUN", "XIUMIN",
    "TAEYONG", "JENO", "HENDERY", "YANGYANG", "GISELLE", "SEULGI",
    "MINO", "B.I", "HyunA&DAWN", "G-DRAGON", "TAEIL", "Henry",
    # 인디·R&B·힙합
    "Crush", "Loco", "Gaho", "BOL4", "SHAUN", "MeloMance",
    "Car, the garden", "Wonstein", "Ugly Duck",
    # 서브유닛
    "Red Velvet - IRENE & SEULGI",
    # 리그 오브 레전드 K-pop 가상 아티스트 (실제 K-pop 보컬 참여)
    "K/DA", "League of Legends", "Seraphine",
}


def _is_kpop(artists_str: str) -> bool:
    """artists 컬럼에 K-pop 아티스트가 한 명이라도 있으면 True"""
    return any(a.strip() in KPOP_ARTISTS for a in str(artists_str).split(";"))


@st.cache_data
def load_data():
    df = pd.read_csv("data/dataset.csv", index_col=0)
    df = df.drop_duplicates(subset=["track_id"])
    df["duration_min"] = df["duration_ms"] / 60000
    return df


@st.cache_data
def load_filtered():
    """비교 대상 장르 6개 필터 + k-pop은 실제 K-pop 아티스트만 포함"""
    df = load_data()
    mask_kpop  = (df["track_genre"] == "k-pop") & df["artists"].apply(_is_kpop)
    mask_other = (df["track_genre"] != "k-pop") & df["track_genre"].isin(COMPARE_GENRES)
    return df[mask_kpop | mask_other].copy()
