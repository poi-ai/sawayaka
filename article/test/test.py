import pandas as pd
import pickle
import numpy as np

# 予測したいテストデータの準備（例）
X_test = pd.DataFrame({
    'store_name': ['store_A', 'store_B', 'store_C', 'store_D', 'store_E',
                   'store_F', 'store_G', 'store_H', 'store_I', 'store_J'],
    'temperature': np.random.rand(10) * 30,  # 温度データ
    'relative_humidity': np.random.rand(10) * 100,  # 湿度データ
    'precipitation': np.random.rand(10),  # 降水量データ
    'rain': np.random.randint(0, 2, 10),  # 雨の有無
    'snowfall': np.random.randint(0, 2, 10),  # 雪の有無
    'weather_code': np.random.randint(1, 10, 10),  # 天気コード
    'month': np.random.randint(1, 13, 10),  # 月
    'hour': np.random.randint(0, 24, 10),  # 時間
    'weekday': np.random.randint(0, 7, 10),  # 曜日
    'consecutive_holidays': np.random.randint(0, 5, 10),  # 連休の長さ
    'holiday_count': np.random.randint(0, 10, 10),  # 休日の数
    'connect_consecutive_holidays': np.random.randint(0, 5, 10),  # 接続連休
    'connect_holiday_count': np.random.randint(0, 10, 10),  # 接続休日の数
    'before_10min_wait_time': (np.random.rand(10) * 10).astype(int)  # 10分前の待ち時間を整数に変換
})

# 学習したランダムフォレストのパイプラインを読み込む
with open('rf_trained_model.pkl', 'rb') as f:
    rf_pipeline = pickle.load(f)

# 学習した勾配ブースティングのパイプラインを読み込む
with open('gb_trained_model.pkl', 'rb') as f:
    gb_pipeline = pickle.load(f)

# テストデータを使ってランダムフォレストの予測を行う
rf_predictions = rf_pipeline.predict(X_test)

# テストデータを使って勾配ブースティングの予測を行う
gb_predictions = gb_pipeline.predict(X_test)

# 予測結果を整数に変換
rf_predictions = rf_predictions.astype(int)
gb_predictions = gb_predictions.astype(int)


# 予測結果を元のデータフレームに追加
X_test['rf_wait_time'] = rf_predictions
X_test['gb_wait_time'] = gb_predictions

# データフレームをCSVファイルとして保存
X_test.to_csv('predictions.csv', index=False)

# 予測結果を表示
print("Random Forest Predictions:")
print(rf_predictions)
print("Gradient Boosting Predictions:")
print(gb_predictions)
print("\nDataFrame with predictions:")
print(X_test)
