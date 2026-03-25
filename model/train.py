import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, BaggingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, validation_curve
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set style untuk plot
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Create saved_model directory if it doesn't exist
os.makedirs("saved_model", exist_ok=True)

# Load data
df = pd.read_csv("data/quran_stats.csv", sep=";")

# Fix format angka - ganti koma jadi titik
df["estimasi_hari"] = df["estimasi_hari"].astype(str).str.replace(",", ".").astype(float)

print("📊 Dataset Info:")
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print("\n📈 Dataset Statistics:")
print(df.describe())

# Feature Engineering
print("\n🔧 Feature Engineering...")
df["rata_kata"] = df["jumlah_kata"] / df["jumlah_ayat"]
df["rata_huruf"] = df["jumlah_huruf"] / df["jumlah_ayat"]
df["rasio_huruf_kata"] = df["jumlah_huruf"] / df["jumlah_kata"]
df["kompleksitas"] = df["jumlah_ayat"] * df["rata_kata"]

# Features dan target``
features = [
    "jumlah_huruf",
    "jumlah_kata",
    "kompleksitas"
]

X = df[features]
y = df["estimasi_hari"]

print(f"\n📋 Features: {features}")
print(f"Target: estimasi_hari")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

print(f"\n� Data Split:")
print(f"Train: {X_train.shape[0]} samples")
print(f"Test: {X_test.shape[0]} samples")

# Preprocessing - Scaling
scaler = None
X_train_scaled = X_train
X_test_scaled = X_test

print("\n🔧 Data preprocessing completed (StandardScaler)")

# Overfitting Analysis - Validation Curve
print("\n📈 Analyzing Overfitting...")

# Test different max_depth values
max_depths = range(1, 21)
train_scores, val_scores = validation_curve(
    RandomForestRegressor(
        n_estimators=100,
        min_samples_leaf=8,
        random_state=42
    ),
    X_train_scaled, y_train,
    param_name='max_depth',
    param_range=max_depths,
    cv=5,
    scoring='neg_mean_squared_error',
    n_jobs=-1
)

# Convert to positive MSE
train_scores = -train_scores
val_scores = -val_scores

# Calculate mean and std
train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
val_mean = np.mean(val_scores, axis=1)
val_std = np.std(val_scores, axis=1)

# Plot validation curve
plt.figure(figsize=(12, 8))

plt.subplot(2, 2, 1)
plt.plot(max_depths, train_mean, 'o-', color='blue', label='Training Score')
plt.fill_between(max_depths, train_mean - train_std, train_mean + train_std, alpha=0.1, color='blue')
plt.plot(max_depths, val_mean, 'o-', color='red', label='Validation Score')
plt.fill_between(max_depths, val_mean - val_std, val_mean + val_std, alpha=0.1, color='red')
plt.xlabel('Max Depth')
plt.ylabel('MSE')
plt.title('Validation Curve (Max Depth)')
plt.legend()
plt.grid(True, alpha=0.3)

# Learning Curve
from sklearn.model_selection import learning_curve

train_sizes = np.linspace(0.1, 1.0, 10)
train_sizes_abs, train_scores_lc, val_scores_lc = learning_curve(
    RandomForestRegressor(
        n_estimators=100,
        max_depth=3,
        min_samples_leaf=8,
        random_state=42
    ),
    X_train_scaled, y_train,
    train_sizes=train_sizes,
    cv=5,
    scoring='neg_mean_squared_error',
    n_jobs=-1
)

train_scores_lc = -train_scores_lc
val_scores_lc = -val_scores_lc

train_mean_lc = np.mean(train_scores_lc, axis=1)
train_std_lc = np.std(train_scores_lc, axis=1)
val_mean_lc = np.mean(val_scores_lc, axis=1)
val_std_lc = np.std(val_scores_lc, axis=1)

plt.subplot(2, 2, 2)
plt.plot(train_sizes_abs, train_mean_lc, 'o-', color='blue', label='Training Score')
plt.fill_between(train_sizes_abs, train_mean_lc - train_std_lc, train_mean_lc + train_std_lc, alpha=0.1, color='blue')
plt.plot(train_sizes_abs, val_mean_lc, 'o-', color='red', label='Validation Score')
plt.fill_between(train_sizes_abs, val_mean_lc - val_std_lc, val_mean_lc + val_std_lc, alpha=0.1, color='red')
plt.xlabel('Training Set Size')
plt.ylabel('MSE')
plt.title('Learning Curve')
plt.legend()
plt.grid(True, alpha=0.3)

# Hyperparameter Grid - Decision Tree
dt_param_grid = {
    "criterion": ["squared_error", "absolute_error"],
    "max_depth": [2, 3, 4, 5],
    "min_samples_split": [10, 15, 20],
    "min_samples_leaf": [5, 8, 10],
    "max_features": ["sqrt", "log2"],
    "splitter": ["best"]
}

# Random Forest Grid
rf_param_grid = {
    "n_estimators": [50, 100],
    "max_depth": [3, 4, 5],
    "min_samples_split": [10, 15],
    "min_samples_leaf": [5, 8],
    "max_features": ["sqrt"]
}

print("\n🔍 Hyperparameter Tuning...")
print(f"DT Grid combinations: {np.prod([len(v) for v in dt_param_grid.values()])}")
print(f"RF Grid combinations: {np.prod([len(v) for v in rf_param_grid.values()])}")

# GridSearchCV untuk Decision Tree
dt = DecisionTreeRegressor(random_state=42)
grid_search_dt = GridSearchCV(
    dt, 
    dt_param_grid, 
    cv=5, 
    scoring="neg_mean_squared_error",
    n_jobs=-1,
    verbose=1
)

# Training Decision Tree
print("\n🌳 Training Decision Tree...")
grid_search_dt.fit(X_train_scaled, y_train)

# Random Forest untuk comparison (lebih robust terhadap overfitting)
rf = RandomForestRegressor(random_state=42)
grid_search_rf = GridSearchCV(
    rf,
    rf_param_grid,
    cv=5,
    scoring="neg_mean_squared_error",
    n_jobs=-1,
    verbose=1
)


rf = RandomForestRegressor(random_state=42)
grid_search_rf = GridSearchCV(
    rf,
    rf_param_grid,
    cv=5,
    scoring="neg_mean_squared_error",
    n_jobs=-1,
    verbose=1
)

print("\n🌲 Training Random Forest (anti-overfitting)...")
grid_search_rf.fit(X_train_scaled, y_train)

# Compare models
dt_score = -grid_search_dt.best_score_
rf_score = -grid_search_rf.best_score_

print(f"\n🏆 Model Comparison:")
print(f"Decision Tree CV MSE: {dt_score:.4f}")
print(f"Random Forest CV MSE: {rf_score:.4f}")

# Choose best model
if rf_score < dt_score:
    print("✅ Random Forest wins - using RF model")
    grid_search = grid_search_rf
    model_type = "RandomForest"
else:
    print("✅ Decision Tree wins - using DT model")
    grid_search = grid_search_dt
    model_type = "DecisionTree"

print("\n🏆 Best Parameters:")
for param, value in grid_search.best_params_.items():
    print(f"  {param}: {value}")

print(f"\n📊 Best CV Score (MSE): {-grid_search.best_score_:.4f}")

# Best model
best_model = grid_search.best_estimator_

# Evaluasi
y_train_pred = best_model.predict(X_train_scaled)
y_test_pred = best_model.predict(X_test_scaled)

print("\n📈 Model Performance:")
print("=" * 40)
print("TRAIN SET:")
print(f"  R² Score: {r2_score(y_train, y_train_pred):.4f}")
print(f"  MSE: {mean_squared_error(y_train, y_train_pred):.4f}")
print(f"  MAE: {mean_absolute_error(y_train, y_train_pred):.4f}")

print("\nTEST SET:")
print(f"  R² Score: {r2_score(y_test, y_test_pred):.4f}")
print(f"  MSE: {mean_squared_error(y_test, y_test_pred):.4f}")
print(f"  MAE: {mean_absolute_error(y_test, y_test_pred):.4f}")

# Feature Importance
print("\n🎯 Feature Importance:")
feature_importance = pd.DataFrame({
    'feature': features,
    'importance': best_model.feature_importances_
}).sort_values('importance', ascending=False)

for _, row in feature_importance.iterrows():
    print(f"  {row['feature']}: {row['importance']:.4f}")

# Residual Analysis
plt.subplot(2, 2, 3)
residuals = y_test - y_test_pred
plt.scatter(y_test_pred, residuals, alpha=0.6)
plt.axhline(y=0, color='red', linestyle='--')
plt.xlabel('Predicted Values')
plt.ylabel('Residuals')
plt.title('Residual Plot')
plt.grid(True, alpha=0.3)

# Feature Importance Plot
plt.subplot(2, 2, 4)
feature_importance_sorted = feature_importance.sort_values('importance', ascending=True)
plt.barh(feature_importance_sorted['feature'], feature_importance_sorted['importance'])
plt.xlabel('Importance')
plt.title('Feature Importance')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('saved_model/model_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# Overfitting Detection
print("\n🔍 Overfitting Analysis:")
print("=" * 40)

# Find optimal depth from validation curve
optimal_depth_idx = np.argmin(val_mean)
optimal_depth = max_depths[optimal_depth_idx]
print(f"Optimal Max Depth: {optimal_depth}")

# Check overfitting indicators
train_final = train_mean[optimal_depth_idx]
val_final = val_mean[optimal_depth_idx]
overfitting_ratio = val_final / train_final

print(f"Training MSE at optimal depth: {train_final:.4f}")
print(f"Validation MSE at optimal depth: {val_final:.4f}")
print(f"Overfitting Ratio (Val/Train): {overfitting_ratio:.4f}")

if overfitting_ratio > 2.0:
    print("🚨 SEVERE OVERFITTING!")
    print("   Model memorizing training data")
    print("   Recommendations:")
    print("   - Use Random Forest instead")
    print("   - Increase min_samples_split to 15+")
    print("   - Increase min_samples_leaf to 8+")
    print("   - Reduce max_depth to 3-4")
    print("   - Collect more training data")
elif overfitting_ratio > 1.5:
    print("⚠️  HIGH OVERFITTING DETECTED!")
    print("   Recommendations:")
    print("   - Increase min_samples_split")
    print("   - Increase min_samples_leaf") 
    print("   - Reduce max_depth")
    print("   - Add more training data")
elif overfitting_ratio > 1.2:
    print("⚠️  MODERATE OVERFITTING")
    print("   Consider regularization")
else:
    print("✅ GOOD GENERALIZATION")
    print("   Model is well-balanced")

# Model Complexity Analysis
best_depth = grid_search.best_params_['max_depth']
if best_depth is not None and best_depth > 10:
    print(f"\n⚠️  Model might be too complex (depth={best_depth})")
elif best_depth is not None and best_depth < 3:
    print(f"\n⚠️  Model might be too simple (depth={best_depth})")
else:
    print(f"\n✅ Model complexity looks good (depth={best_depth})")

# Save model dan scaler
joblib.dump(best_model, "saved_model/model.pkl")
joblib.dump(scaler, "saved_model/scaler.pkl")
joblib.dump(features, "saved_model/features.pkl")
joblib.dump(model_type, "saved_model/model_type.pkl")

print("\n✅ Model, scaler, dan features berhasil disimpan!")
print("📁 Files:")
print("  - saved_model/model.pkl")
print("  - saved_model/scaler.pkl") 
print("  - saved_model/features.pkl")
print("  - saved_model/model_analysis.png")

print("\n📊 Grafik analisis tersimpan di: saved_model/model_analysis.png")
print("   Grafik menunjukkan:")
print("   1. Validation Curve - deteksi overfitting vs max_depth")
print("   2. Learning Curve - performa vs ukuran dataset") 
print("   3. Residual Plot - distribusi error prediksi")
print("   4. Feature Importance - kontribusi setiap fitur")