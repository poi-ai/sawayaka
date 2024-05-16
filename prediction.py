import config
import japanize_matplotlib # グラフ日本語表示に必要なので消さない
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import pickle
import requests
import time
from holiday import Holiday
from log import Log
from datetime import datetime, timedelta, timezone


class Main(Holiday):
    def __init__(self):
        self.log = Log()

    def main(self):
        self.log.info('さわやか待ち時間更新スクリプト開始')

        # 現在時刻を取得
        self.now = datetime.now(timezone.utc) + timedelta(hours = 9)

        # Holidays JP APIから祝日一覧を取得
        holiday_list = self.get_holidays()

        # 連休情報の補正
        holiday_list = self.correction_holidays(holiday_list)

        # 連休情報の計算
        consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count = self.calc_holidays(holiday_list)

        # Meteo APIから今日1日の天気データを取得する
        weather_info = self.get_weather()

        # 学習済みモデルの読み込み
        self.get_model()

        # 店舗ごとに画像URLを格納するリスト
        prediction_image_list = []

        # 店舗ごとに予測を行う
        for store_id in range(1, 35):
            # 待ち時間設定用
            before_wait_time = -1
            wait_time_list = []

            # 時間ごとに予測を行う
            for hour in range(9, 23):
                for minute in range(0, 60, 10):
                    # 天気データを予測用のDataFrameに充てる
                    prediction_data = self.mold_weather_info(weather_info, hour)

                    # 足りないデータを埋めていく
                    prediction_data['store_name'] = store_id
                    prediction_data['month'] = self.now.month
                    # prediction_data['minute'] = minute
                    prediction_data['weekday'] = self.now.weekday
                    prediction_data['consecutive_holidays'] = consecutive_holidays
                    prediction_data['holiday_count'] = holiday_count
                    prediction_data['connect_consecutive_holidays'] = connect_consecutive_holidays
                    prediction_data['connect_holiday_count'] = connect_holiday_count
                    prediction_data['before_10min_wait_time'] = before_wait_time

                    # 加工したデータを学習済みモデルにあて、予測を行う
                    wait_time = self.prediction_wait_time(prediction_data)
                    wait_time_list.append(wait_time)
                    before_wait_time = wait_time
                    #print(f'{hour}:{minute} {wait_time}')

            # 予測データから画像の作成
            image_name, image_path = self.create_prediction_image(wait_time_list, store_id)

            # 予測データの画像投稿,URL取得
            image_url = self.post_gyazo_api(image_name, image_path)

            # 予測データの格納
            prediction_image_list.append({'store_id': store_id, 'image_url': image_url})

            exit()

        # TODO URLと予測データ(と待ち時間)をHTMLに埋め込みWebサイトへ投稿

        self.log.info('さわやか待ち時間更新スクリプト終了')

    def get_weather(self):
        '''
        静岡県庁の1日分の天候情報をOpen Meteo APIから取得する

        Returns:
            weather_info(dict): 天候情報
                time(list[str,str...]): 時刻
                temperature_2m(list[float,float,...]): 気温(℃)
                relative_humidity_2m(list[int,int,...]): 湿度(%)
                precipitation(list[float,float,...]): 降水量(mm) [降雨量+降雪量]
                rain(list[float,float,...]): 降雨量(mm)
                snowfall(list[float,float,...]): 降雪量(cm)
                weather_code(list[int,int,...]): 天気コード
                    https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
        '''
        # API呼び出し
        weather_api_url = 'https://api.open-meteo.com/v1/forecast'
        weather_api_params = {
            'latitude': 34.976944,
            'longitude': 138.383056,
            'hourly': 'temperature_2m,relative_humidity_2m,precipitation,rain,snowfall,weather_code',
            'timezone': 'Asia/Tokyo',
            'forecast_days': 1
        }

        try:
            r = requests.get(weather_api_url, params = weather_api_params)
        except Exception as e:
            self.log.error(f'天候情報取得APIエラー\n{e}')
            self.log.info(f'再取得します')
            time.sleep(10)
            try:
                r = requests.get(weather_api_url, params = weather_api_params)
            except:
                self.log.error(f'天候情報取得APIエラー\n{e}')
                return False

        if r.status_code != 200:
            self.log.error(f'天候情報取得APIエラー ステータスコード: {r.status_code}')
            return False

        weather_info = r.json()['hourly']

        if len(weather_info) == 0:
            self.log.error(f'天候情報取得APIエラー レスポンス情報が空')
            return False

        return weather_info

    def mold_weather_info(self, weather_info, hour):
        '''
        天気データを予測できるデータに加工する

        Args:
            weather_info(dict): 天気予報データ
            hour(int): x時のデータを予測するか
        '''
        return pd.DataFrame({
            'temperature': [weather_info['temperature_2m'][hour]], # DFを作るときは1つ目の値はlistにしないといけないpdの謎仕様
            'relative_humidity': weather_info['relative_humidity_2m'][hour],
            'precipitation': weather_info['precipitation'][hour],
            'rain': weather_info['rain'][hour],
            'snowfall': weather_info['snowfall'][hour],
            'weather_code': weather_info['weather_code'][hour],
            'hour': hour
        })

    def get_model(self):
        '''学習済みモデルをインスタンス変数に持たせておく'''
        with open('./data/rf_trained_model.pkl', 'rb') as f:
            self.rf_pipeline = pickle.load(f)

        with open('./data/gb_trained_model.pkl', 'rb') as f:
            self.gb_pipeline = pickle.load(f)

        return True

    def prediction_wait_time(self, df, type = 1):
        '''待ち時間の予測を行う'''

        # ランダムフォレスト
        if type == 1:
            return self.rf_pipeline.predict(df).astype(int)[0]

        # 勾配ブースティング
        else:
            return self.gb_pipeline.predict(df).astype(int)[0]

    def create_prediction_image(self, wait_time_list, store_id):
        '''
        予測データをグラフ化・画像化する

        Args:
            wait_time_list(list[int,int...]): 待ち時間データ
            store_id(int): 店舗ID

        Returns:
            file_name(str): 画像ファイル名
            file_path(str): 画像ファイルパス
        '''

        # 画像ファイル名・ファイルパス作成
        file_name = f'{self.now.strftime("%Y%m%d")}_{store_id}'
        file_path = f'./image/{file_name}.png'

        # 横軸(09:00~23:00)のためのリストを作成
        start_time = datetime.strptime('09:00', '%H:%M')
        end_time = datetime.strptime('22:55', '%H:%M')
        time_intervals = int((end_time - start_time).seconds / 600)
        times = [start_time + timedelta(minutes=10 * i) for i in range(time_intervals + 1)]

        # グラフを描画
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(times, wait_time_list, linestyle='-', color='b')

        # 横軸のフォーマットを設定
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)

        # グラフのラベルとタイトル
        ax.set_xlabel('時刻')
        ax.set_ylabel('待ち時間(分)')
        ax.set_title(f'TODO店の待ち時間予測（{self.now.strftime("%Y/%m/%d")}）')

        # グリッド表示
        ax.grid(True)

        # 位置調整(グラフ下に空白追加)
        plt.subplots_adjust(bottom = 0.15)

        # 画像を保存
        plt.savefig(file_path)
        plt.close()

        return file_name, file_path

    def post_gyazo_api(self, image_name, image_path):
        '''
        Gyazo APIを用いて画像をアップロードする

        Args:
            image_name(str): 画像ファイル名
            image_path(str): 画像ファイルの相対パス

        Returns:
            image_url(str): アップロード画像のURL
        '''
        # ヘッダーの設定
        headers = {'Authorization': f'Bearer {config.GYAZO_ACCESS_TOKEN}'}

        # 画像のバイナリ変換
        with open(image_path, 'rb') as f:
            files = {'imagedata': f.read()}

        # リクエスト送信
        response = requests.post('https://upload.gyazo.com/api/upload', headers = headers, files = files, data = {'desc': image_name})
        response.raise_for_status()

        # ステータスチェック
        if response.status_code != 200:
            # TODO エラー処理
            return False

        # レスポンスデータ変換
        response_data = response.json()
        return response_data["url"]

m = Main()
m.main()