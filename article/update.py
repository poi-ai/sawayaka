import pandas as pd
import numpy as np
from tqdm import tqdm

# CSVファイルの読み込み
df = pd.read_csv('sawayaka_data.csv')

# datetime型の列を作成
df['datetime'] = pd.to_datetime(df[['month', 'day', 'hour', 'minute']].assign(year=2024), errors='coerce')

# 不正な日付を持つ行を削除
df = df.dropna(subset=['datetime'])

# 10分前の時間を計算
df['before_10min_datetime'] = df['datetime'] - pd.Timedelta(minutes=10)

# 10分前のwait_timeを取得
df['before_10min_wait_time'] = -1  # 初期値として-1を設定

# 参照用のdataframeを作成
df_copy = df[['store_name', 'wait_time', 'datetime']].copy()

# 10分前のデータを書き込み
for index, row in tqdm(df.iterrows(), total=len(df)):
    mask = (df_copy['store_name'] == row['store_name']) & (df_copy['datetime'] == row['before_10min_datetime'])
    match_index = np.flatnonzero(mask)
    if len(match_index) > 0:
        df.at[index, 'before_10min_wait_time'] = df_copy.at[match_index[0], 'wait_time']

# 不要な列を削除
df = df.drop(columns=['datetime', 'before_10min_datetime'])

# 書き換えたCSVファイルを保存
df.to_csv('update_sawayaka_data.csv', index=False)
