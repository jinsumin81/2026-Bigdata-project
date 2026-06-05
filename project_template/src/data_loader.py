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


@st.cache_data
def load_data():
    df = pd.read_csv("data/dataset.csv", index_col=0)
    df = df.drop_duplicates(subset=["track_id"])
    df["duration_min"] = df["duration_ms"] / 60000
    return df


@st.cache_data
def load_filtered():
    df = load_data()
    return df[df["track_genre"].isin(COMPARE_GENRES)].copy()
