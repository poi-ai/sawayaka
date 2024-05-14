### 集めたデータを元に学習を行う

import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

# データの読み込み
data = pd.read_csv('sort_sawayaka_data.csv')

# 不要なカラムを削除
data.drop(['wait_count', 'day', 'minute'], axis=1, inplace=True)

# 説明変数と目的変数に分割
X = data.drop('wait_time', axis=1)
y = data['wait_time']

# 説明変数を数値変数とカテゴリ変数に分割
numeric_features = ['temperature', 'relative_humidity', 'precipitation', 'rain', 'snowfall', 'consecutive_holidays', 'holiday_count', 'connect_consecutive_holidays', 'connect_holiday_count']
categorical_features = ['store_name', 'weather_code', 'weekday', 'month', 'hour']

# データをトレーニングセットとテストセットに分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


# パイプラインの作成
numeric_transformer = Pipeline(steps=[
    ('num', 'passthrough') # 数値変数はそのまま使用
])

categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore')) # カテゴリ変数はOneHotEncoding
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ])

# ランダムフォレストのパイプライン
rf_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('rf_regressor', RandomForestRegressor(random_state=42))
])

# 勾配ブースティングのパイプライン
gb_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('gb_regressor', GradientBoostingRegressor(random_state=42))
])

# ランダムフォレストの学習
rf_pipeline.fit(X_train, y_train)

# 勾配ブースティングの学習
gb_pipeline.fit(X_train, y_train)

# ランダムフォレストのパイプラインをpickle形式で保存
with open('rf_trained_model.pkl', 'wb') as f:
    pickle.dump(rf_pipeline, f)

# 勾配ブースティングのパイプラインをpickle形式で保存
with open('gb_trained_model.pkl', 'wb') as f:
    pickle.dump(gb_pipeline, f)

# ランダムフォレストの性能評価
rf_train_preds = rf_pipeline.predict(X_train)
rf_test_preds = rf_pipeline.predict(X_test)

print("Random Forest Training RMSE:", mean_squared_error(y_train, rf_train_preds, squared=False))
print("Random Forest Test RMSE:", mean_squared_error(y_test, rf_test_preds, squared=False))

# 勾配ブースティングの性能評価
gb_train_preds = gb_pipeline.predict(X_train)
gb_test_preds = gb_pipeline.predict(X_test)

print("Gradient Boosting Training RMSE:", mean_squared_error(y_train, gb_train_preds, squared=False))
print("Gradient Boosting Test RMSE:", mean_squared_error(y_test, gb_test_preds, squared=False))
