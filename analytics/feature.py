import pandas as pd
import matplotlib.pyplot as plt

# データの読み込み
data = pd.read_csv('sort_sawayaka_data.csv')

# 不要なカラムを削除
data.drop(['wait_count', 'day', 'minute'], axis=1, inplace=True)

# カテゴリ変数をOne-Hot Encodingする
categorical_features = ['store_name', 'weather_code', 'weekday','month','hour']
data_encoded = pd.get_dummies(data, columns=categorical_features, drop_first=True)

# 目的変数を取り除いて相関計算
correlation_matrix = data_encoded.drop('wait_time', axis=1).corrwith(data_encoded['wait_time'])

# 上位20カラムを抽出
top_20_correlated = correlation_matrix.abs().sort_values(ascending=False).head(20).index
top_20_correlation_values = correlation_matrix[top_20_correlated]

# グラフで表示
plt.figure(figsize=(10, 8))
top_20_correlation_values.plot(kind='bar', color=top_20_correlation_values.apply(lambda x: 'red' if x > 0 else 'blue'))
plt.title('Top 20 Correlated Features with Wait Time')
plt.xlabel('Features')
plt.ylabel('Correlation with Wait Time')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
