import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder

# データの読み込み
data = pd.read_csv('update_sawayaka_data.csv')

# 不要なカラムを削除
data.drop(['wait_count', 'day', 'minute'], axis=1, inplace=True)

# カテゴリ変数をOne-Hot Encodingする
categorical_features = ['store_name', 'weather_code', 'weekday','month','hour']
data_encoded = pd.get_dummies(data, columns=categorical_features, drop_first=True)

# 目的変数を取り除いて相関計算
correlation_matrix = data_encoded.drop('wait_time', axis=1).corrwith(data_encoded['wait_time'])
correlation_matrix = correlation_matrix.abs().sort_values(ascending=False)

# 上位20カラムを抽出
top_20_correlated = correlation_matrix.head(20)

# グラフで表示
plt.figure(figsize=(10, 8))
top_20_correlated.plot(kind='bar')
plt.title('Top 20 Correlated Features with Wait Time')
plt.xlabel('Features')
plt.ylabel('Absolute Correlation with Wait Time')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
