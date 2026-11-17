"""Train and evaluate a construction-material text classifier.

Run from the demo_genai repository root:
    python scripts/train_evaluate_materials.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

DATA_PATH = Path("data/processed/construction_materials_clean.csv")
MODEL_PATH = Path("models/material_classifier.joblib")
RESULTS_PATH = Path("outputs/material_evaluation.json")
SEED = 42

# These are material *families*, not random test examples. All descriptions
# containing these names are excluded from training and validation.
# Edit this list BEFORE inspecting final test results, and keep it fixed.
UNSEEN_MATERIALS = {
    "Concrete": [r"\b(?:portland cement|cement mortar|betonmortel)\b"],
    "Metals": [r"\b(?:copper pipe|koperen buis|steel mesh)\b"],
    "Wood": [r"\b(?:mdf panel|hardhouten plank|oak flooring boards)\b"],
    "Insulation": [r"\b(?:acoustic insulation panel|dakisolatie)\b"],
    "Glass": [r"\b(?:float glass|gelaagd glas)\b"],
}


def template_group(text: str) -> str:
    """Heuristic near-template grouping; inspect groups for your own data."""
    text = text.casefold()
    text = re.sub(r"\b(?:po|ref|order)[-\s:]?\d+\b", "<ref>", text)
    text = re.sub(r"\d+(?:[.,/]\d+)*", "<num>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_split(frame: pd.DataFrame, test_size: float, seed: int):
    groups = frame["description_clean"].map(template_group)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(frame, frame["category"], groups))
    return frame.iloc[train_idx].copy(), frame.iloc[test_idx].copy()


def evaluate(model: Pipeline, frame: pd.DataFrame, name: str, labels: list[str]):
    if frame.empty:
        print(f"\n{name}: no examples; add matching examples to the dataset")
        return {"n": 0, "status": "empty"}
    predicted = model.predict(frame["description_clean"])
    truth = frame["category"]
    print(f"\n=== {name} (n={len(frame)}) ===")
    print(classification_report(truth, predicted, labels=labels, zero_division=0))
    print("Confusion matrix (rows=true, columns=predicted):")
    print(pd.DataFrame(confusion_matrix(truth, predicted, labels=labels), index=labels, columns=labels))
    return {
        "n": int(len(frame)),
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_f1": float(f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(truth, predicted, labels=labels, average="weighted", zero_division=0)),
    }


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing {DATA_PATH}; run the cleaning notebook first")

    df = pd.read_csv(DATA_PATH)
    required = {"description_clean", "category"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df = df.dropna(subset=["description_clean", "category"]).copy()
    df["description_clean"] = df["description_clean"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df = df[df["description_clean"].ne("")].copy()
    df = df.drop_duplicates(subset=["description_clean", "category"])

    # A text with conflicting labels cannot be used as reliable ground truth.
    conflicts = df.groupby("description_clean")["category"].nunique()
    bad_texts = set(conflicts[conflicts > 1].index)
    if bad_texts:
        print(f"Removing {len(bad_texts)} conflicting descriptions")
        df = df[~df["description_clean"].isin(bad_texts)].copy()

    labels = sorted(df["category"].unique())
    if len(labels) < 2:
        raise ValueError("At least two categories are required")

    # Freeze the unseen-name challenge set before any training.
    unseen_mask = pd.Series(False, index=df.index)
    for category, patterns in UNSEEN_MATERIALS.items():
        category_mask = df["category"].eq(category)
        for pattern in patterns:
            unseen_mask |= category_mask & df["description_clean"].str.contains(
                pattern, case=False, regex=True, na=False
            )
    unseen = df[unseen_mask].copy()
    known = df[~unseen_mask].copy()

    # Exclude entire near-template groups from the known-material training pool.
    # This avoids the same template appearing in both train and test sets.
    held_groups = set(unseen["description_clean"].map(template_group))
    known = known[~known["description_clean"].map(template_group).isin(held_groups)].copy()

    # Group-disjoint train/validation/test splitting.
    train_val, test = make_split(known, test_size=0.20, seed=SEED)
    train, validation = make_split(train_val, test_size=0.20, seed=SEED + 1)

    if set(train["category"]) != set(labels):
        raise ValueError("Training split lacks one or more categories; enlarge the dataset")

    # Noise type was produced by the synthetic generator; if absent, report
    # that clean/noisy evaluation cannot be distinguished reliably.
    if "noise_type" in test.columns:
        noise = test["noise_type"].fillna("none").astype(str).str.strip().str.lower()
        clean_test = test[noise.isin(["none", "", "nan"])].copy()
        noisy_test = test[~noise.isin(["none", "", "nan"])].copy()
    else:
        print("WARNING: noise_type column missing. Clean/noisy test sets unavailable.")
        clean_test = test.iloc[0:0].copy()
        noisy_test = test.iloc[0:0].copy()

    print("Dataset sizes:", {
        "train": len(train), "validation": len(validation),
        "clean_test": len(clean_test), "noisy_test": len(noisy_test),
        "unseen_test": len(unseen),
    })
    print("Training category counts:", train["category"].value_counts().to_dict())

    # Tune using validation only. The vectorizer is fitted inside each pipeline
    # using the training split, never using validation or test text.
    candidates = [
        {"ngram_range": (1, 2), "C": 1.0},
        {"ngram_range": (1, 2), "C": 3.0},
        {"ngram_range": (1, 3), "C": 1.0},
    ]
    best_score, best_model, best_params = -1.0, None, None
    for params in candidates:
        model = Pipeline([
            ("tfidf", TfidfVectorizer(
                lowercase=True, ngram_range=params["ngram_range"],
                sublinear_tf=True, min_df=1
            )),
            ("classifier", LogisticRegression(
                C=params["C"], max_iter=2000, class_weight="balanced",
                random_state=SEED
            )),
        ])
        model.fit(train["description_clean"], train["category"])
        score = f1_score(
            validation["category"], model.predict(validation["description_clean"]),
            average="macro", zero_division=0
        )
        print(f"Validation: {params} => macro F1={score:.3f}")
        if score > best_score:
            best_score, best_model, best_params = score, model, params

    print("Selected hyperparameters:", best_params)
    print(f"Validation macro F1: {best_score:.3f}")

    # Refit with the selected hyperparameters on train+validation only.
    final_train = pd.concat([train, validation], ignore_index=True)
    final_model = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=best_params["ngram_range"],
            sublinear_tf=True, min_df=1
        )),
        ("classifier", LogisticRegression(
            C=best_params["C"], max_iter=2000, class_weight="balanced",
            random_state=SEED
        )),
    ])
    final_model.fit(final_train["description_clean"], final_train["category"])

    results = {
        "selected_params": {"ngram_range": list(best_params["ngram_range"]), "C": best_params["C"]},
        "validation_macro_f1": float(best_score),
        "clean": evaluate(final_model, clean_test, "Clean known-material test", labels),
        "noisy": evaluate(final_model, noisy_test, "Noisy known-material test", labels),
        "unseen": evaluate(final_model, unseen, "Unseen-material-name test", labels),
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved model: {MODEL_PATH}")
    print(f"Saved evaluation: {RESULTS_PATH}")
    print("NOTE: Synthetic results are not an estimate of real-world invoice performance.")


if __name__ == "__main__":
    main()
