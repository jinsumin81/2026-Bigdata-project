import pandas as pd
from sklearn.preprocessing import StandardScaler

AUDIO_FEATURES = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "liveness", "speechiness", "loudness", "tempo",
    "duration_ms", "key", "mode"
]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["track_id"])
    df = df.dropna(subset=AUDIO_FEATURES + ["popularity"])
    df = df[df["popularity"] > 0].copy()
    df["duration_min"] = df["duration_ms"] / 60000
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    threshold = df["popularity"].quantile(0.8)
    df = df.copy()
    df["popularity_group"] = (df["popularity"] >= threshold).map(
        {True: "high", False: "low"}
    )
    return df


def get_X_y(df: pd.DataFrame):
    df_clean = clean(df)
    X = df_clean[AUDIO_FEATURES].copy()
    y = df_clean["popularity"]
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X), columns=AUDIO_FEATURES, index=X.index
    )
    return X_scaled, y, scaler
