import pandas as pd
import random

def load_sample_data(path="src/data/issues.csv"):
    return pd.read_csv(path)

def get_random_samples(df, n=5):
    return df.sample(n=n)

def evaluate_prediction(sample_row, predict_fn):
    summary = sample_row["Summary"]
    description = sample_row["Description"]
    actual_team = sample_row["Fixed By"]
    predicted_team = predict_fn(summary, description)
    return {
        "summary": summary,
        "description": description,
        "predicted": predicted_team,
        "actual": actual_team,
        "is_correct": predicted_team == actual_team
    }
