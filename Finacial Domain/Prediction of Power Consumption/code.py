import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt
import seaborn as sns

# Load the dataset with error handling for bad lines
data_path = '/kaggle/input/power-consumption/power-laws-forecasting-energy-consumption-holidays.csv'
data = pd.read_csv(data_path, on_bad_lines='skip')

# Inspect the data
print(data.head())
print(data.info())
print(data.describe())

# Extract datetime features
data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
data = data.dropna(subset=['timestamp'])  # Drop rows where timestamp conversion failed
data['year'] = data['timestamp'].dt.year
data['month'] = data['timestamp'].dt.month
data['day'] = data['timestamp'].dt.day
data['hour'] = data['timestamp'].dt.hour
data['dayofweek'] = data['timestamp'].dt.dayofweek

# Identify target and feature columns
target = 'consumption'  # Replace with the actual target column name if different
features = data.columns.drop([target, 'timestamp'])

# Separate numerical and categorical columns
num_cols = data.select_dtypes(include=['float64', 'int64']).columns.drop(target)
cat_cols = data.select_dtypes(include=['object']).columns

# Define preprocessing steps for numerical and categorical data
num_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

cat_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

# Combine preprocessing steps
preprocessor = ColumnTransformer(
    transformers=[
        ('num', num_transformer, num_cols),
        ('cat', cat_transformer, cat_cols)
    ])

# Define the full pipeline including polynomial features and the regression model
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('poly_features', PolynomialFeatures(degree=2, include_bias=False)),
    ('model', LinearRegression())
])

# Define parameter grid for GridSearchCV
param_grid = {
    'poly_features__degree': [1, 2, 3],
    'model': [LinearRegression(), Ridge(), Lasso()],
    'model__alpha': [0.1, 1.0, 10.0]
}

# Split data into training and testing sets
X = data[features]
y = data[target]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Perform grid search with cross-validation
grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='r2', n_jobs=-1)
grid_search.fit(X_train, y_train)

# Best model and its parameters
best_model = grid_search.best_estimator_
print(f"Best model: {grid_search.best_params_}")

# Evaluate the best model on test data
y_pred = best_model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"Test MSE: {mse:.2f}, Test MAE: {mae:.2f}, Test R^2: {r2:.2f}")

# Plot predicted vs true energy consumption
plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred, alpha=0.5)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'k--', lw=2)
plt.xlabel('True Consumption')
plt.ylabel('Predicted Consumption')
plt.title('True vs Predicted Energy Consumption')
plt.show()

# Cross-validation scores
cv_scores = cross_val_score(best_model, X, y, cv=5, scoring='r2')
print(f"Cross-Validation R^2 Scores: {cv_scores}")
print(f"Mean CV R^2 Score: {np.mean(cv_scores)}")

# Feature importance analysis (coefficients for linear models)
if hasattr(best_model.named_steps['model'], 'coef_'):
    feature_importance = best_model.named_steps['model'].coef_
    feature_names = best_model.named_steps['poly_features'].get_feature_names_out(num_cols)
    feature_importance_df = pd.DataFrame({'feature': feature_names, 'importance': feature_importance})
    feature_importance_df = feature_importance_df.sort_values(by='importance', ascending=False)

    # Plot feature importance
    plt.figure(figsize=(10, 8))
    sns.barplot(x='importance', y='feature', data=feature_importance_df)
    plt.title('Feature Importance')
    plt.show()

# Correlation heatmap of features
plt.figure(figsize=(10, 8))
sns.heatmap(data.corr(), annot=True, cmap='coolwarm')
plt.title('Correlation Heatmap')
plt.show()

# Time series analysis
data.set_index('timestamp', inplace=True)
data['predicted_consumption'] = np.nan
data.loc[X_test.index, 'predicted_consumption'] = y_pred

# Plot actual vs predicted consumption over time
plt.figure(figsize=(14, 8))
data[['consumption', 'predicted_consumption']].plot()
plt.xlabel('Timestamp')
plt.ylabel('Energy Consumption')
plt.title('Actual vs Predicted Energy Consumption Over Time')
plt.legend(['Actual Consumption', 'Predicted Consumption'])
plt.show()
