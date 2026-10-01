---
name: ml-review
description: Review machine learning code WITHOUT modifying it - data leakage, train/validation/test splits, reproducibility (seeds, data versions), evaluation and metrics, class imbalance, and MLflow tracking/registration - for scikit-learn, XGBoost, LightGBM and Spark ML (pyspark.ml) on Databricks. Use when the user asks to review, audit or sanity-check model training, feature engineering, evaluation or MLflow code. Do NOT use for general code design reviews (use design-review) or Spark performance (use pyspark-optimize).
---

# ML review

Goal: catch the mistakes that make a model look better offline than it will be in production, and the gaps that make results impossible to reproduce. Do not edit files; report findings.

## Workflow

1. **Map the pipeline**: where data is loaded, how the target is built, where the split happens, which preprocessing is fitted, how the model is trained, evaluated and logged. Identify the library: scikit-learn / XGBoost / LightGBM (pandas) or Spark ML (`pyspark.ml`).
2. **Check each lens below**, in order. Verify every finding in the code; drop speculative ones.
3. **Report** with the same format as `design-review` (Summary, numbered Findings with severity, file:line, why it matters, concrete suggestion; What is good). Leakage and evaluation errors are **High** by default.

## 1. Data leakage (highest priority)

- **Fitted before the split**: scalers, encoders, imputers, feature selection, PCA, target encoding fitted on the full dataset.
  - scikit-learn: put preprocessing inside a `Pipeline` / `ColumnTransformer` and fit only on train; in CV, the pipeline is refitted per fold automatically.
  - Spark ML: `StringIndexer`, `OneHotEncoder`, `Imputer`, `StandardScaler`, `VectorAssembler`+`MinMaxScaler`… must be stages of a `Pipeline` that is `.fit()` on the **train** DataFrame after `randomSplit`.
- **Target leakage**: features computed with information from after the prediction moment (future transactions, post-event status, aggregates over the whole period including the label window).
- **Time series**: random split where a temporal split is required; rolling features that include the current/future row; use `TimeSeriesSplit` or split by date.
- **Group leakage**: the same customer/entity in train and test when the model will predict on new entities → `GroupKFold` / split by entity id.
- **Duplicates** across train and test.
- **Tuning on the test set**: hyperparameters or thresholds chosen with test data; the test set must be used once, at the end.

## 2. Splits and validation

- Stratified split for classification (`stratify=y`; in Spark, `sampleBy` per class or split by a hashed id).
- Spark `randomSplit` is not deterministic unless the input order is stable: set `seed` **and** avoid re-computing the source in between (cache or persist the input of the split, or split by a hashed id column).
- Cross-validation (`cross_val_score`, `CrossValidator`/`TrainValidationSplit`) with an explicit seed.

## 3. Reproducibility

- Seeds: `random_state` (scikit-learn, XGBoost `random_state`, LightGBM `seed`/`random_state`), Spark ML `seed` params, `numpy` seed when relevant.
- Data version: log the table name and Delta version/timestamp used to train (`DESCRIBE HISTORY`, `versionAsOf`), or the query date range.
- Pinned library versions (they are in the MLflow model environment if logged properly).

## 4. Evaluation and metrics

- Metric matches the problem: imbalanced classification → PR-AUC, recall/precision at the operating threshold, F1; not accuracy alone. Regression → MAE/RMSE and the error distribution, not only R².
- A **baseline** (majority class, last value, simple model) to compare against.
- Threshold chosen on validation data, documented.
- Metrics reported per relevant segment when the business cares (region, product).
- Probability calibration if scores are used as probabilities.

## 5. MLflow (Databricks)

- `mlflow.set_experiment(...)` explicit; one run per training; params, metrics and tags (data version, git commit) logged.
- Model logged with the right flavor: `mlflow.sklearn`, `mlflow.xgboost`, `mlflow.lightgbm`, `mlflow.spark`, **with `signature` and `input_example`**.
- Registered in Unity Catalog (`models:/catalog.schema.model`) and referenced by **alias** (`@champion`/`@challenger`), not by hard-coded version numbers.
- Autologging is fine, but check it does not log the test set metrics as if they were validation.

## 6. Scale and Spark specifics

- `toPandas()` of a large dataset to train scikit-learn models: sample, aggregate first, or use Spark ML / distributed training.
- Batch scoring with Spark: `mlflow.pyfunc.spark_udf` for non-Spark models instead of collecting data to the driver.
- Feature engineering done identically in training and scoring (shared function or the same fitted `PipelineModel`).
