import numpy as np
import pandas as pd
import pickle
import requests
import time
from log import Log
from datetime import datetime, timedelta, timezone

class Main():
    def __init__(self):
        self.log = Log()

    def main(self):
        self.log.info('さわやか待ち時間更新スクリプト開始')

        # 現在時刻を取得
        now = datetime.now(timezone.utc) + timedelta(hours = 9)

        # Holidays JP APIから祝日一覧を取得
        holiday_list = self.get_holidays()

        # 連休情報の補正
        holiday_list = self.correction_holidays(holiday_list, now)

        # 連休情報の計算
        consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count = self.calc_holidays(holiday_list, now)

        # Meteo APIから1日分の天気データを取得する
        weather_info = self.get_weather()

        # 店舗ごとに予測を行う
        for store_id in range(1, 35):
            # 待ち時間設定用
            before_wait_time = -1

            # 時間ごとに予測を行う
            for hour in range(9, 23):
                for minute in range(0, 60, 10):
                    # 天気データを予測用のDataFrameに充てる
                    prediction_data = self.mold_weather_info(weather_info, hour)

                    # 足りないデータを埋めていく
                    prediction_data['store_name'] = store_id
                    prediction_data['month'] = now.month
                    prediction_data['weekday'] = now.weekday
                    prediction_data['consecutive_holidays'] = consecutive_holidays
                    prediction_data['holiday_count'] = holiday_count
                    prediction_data['connect_consecutive_holidays'] = connect_consecutive_holidays
                    prediction_data['connect_holiday_count'] = connect_holiday_count
                    prediction_data['before_10min_wait_time'] = before_wait_time

                    # 加工したデータを学習済みモデルにあて、予測を行う
                    wait_time = self.prediction_wait_time(prediction_data)
                    print(wait_time)
                    before_wait_time = wait_time
            exit()

        # TODO 予測データから画像の作成

        # TODO 予測データの画像投稿,URL取得

        # TODO URLと予測データをHTMLに埋め込みWebサイトへ投稿

        self.log.info('さわやか待ち時間更新スクリプト終了')

    def get_holidays(self):
        '''
        Holidays JP APIから祝日情報を取得する

        Returns:
            holidays(dict): 実行日の昨年～来年までの祝日一覧

        '''
        try:
            r = requests.get('https://holidays-jp.github.io/api/v1/date.json')
        except Exception as e:
            self.log.error(f'祝日情報取得APIエラー\n{e}')
            return False

        if r.status_code != 200:
            self.log.error(f'祝日情報取得APIエラー ステータスコード: {r.status_code}')
            return False

        holidays = r.json()

        if len(holidays) == 0:
            self.log.error(f'祝日情報取得APIエラー レスポンス情報が空')
            return False

        return holidays

    def correction_holidays(self, holiday_list, now):
        '''
        祝日ではないが休みを取る人が多い日付を祝日リストに追加する
        (年末年始・お盆の追加)

        Args:
            holiday_list(dict): 実行日の昨年～来年までの祝日一覧
            now(datetime.datetime): 現在時刻

        Returns:
            holiday_list(dict): 修正後の祝日一覧

        '''
        # 追加対象の日付
        add_dict = {}

        # 昨年から今年の年末年始を追加
        add_dict = self.add_holiday_elements(add_dict,
                                             start_date = now.replace(year = now.year - 1, month = 12, day = 29),
                                             end_date = now.replace(month = 1, day = 3),
                                             param_name = '年末年始')

        # 今年のお盆を追加
        add_dict = self.add_holiday_elements(add_dict,
                                             start_date = now.replace(month = 8, day = 13),
                                             end_date = now.replace(month = 8, day = 16),
                                             param_name = 'お盆')

        # 今年から来年の年末年始を追加
        add_dict = self.add_holiday_elements(add_dict,
                                             start_date = now.replace(month = 12, day = 29),
                                             end_date = now.replace(year = now.year + 1, month = 1, day = 3),
                                             param_name = '年末年始')

        # 重複削除で祝日情報を合体
        holiday_list.update(add_dict)

        return holiday_list

    def add_holiday_elements(self, add_dict, start_date, end_date, param_name):
        '''
        追加連休情報を祝日フォーマットに沿った形で追加する

        Args:
            add_dict(dict): 連休情報を格納したい辞書
            start_date(datetime.datetime): 追加したい連休の初日の日付
            end_date(datetime.datetime): 追加したい連休の最終日の日付
            param_name(str): 連休の値名

        Returns:
            add_dict(dict): 連休情報追加後の辞書

        '''
        while start_date <= end_date:
            add_dict[start_date.strftime('%Y-%m-%d')] = param_name
            start_date += timedelta(days = 1)

        return add_dict

    def calc_holidays(self, holiday_list, now):
        '''
        連休日数・連休何日目かを計算する

        Args:
            holiday_list(dict): 実行日の昨年～来年までの祝日一覧
            now(datetime.datetime): 現在時刻

        Returns:
            consecutive_holidays(int): 今日の休みは何連休か
            holiday_count(int): 今日は連休の何日目か
            connect_consecutive_holidays(int): 3日以内の営業日を休みにした場合の連休日数
            connect_holiday_count(int): 3日以内の営業日を休みにした場合の連休何日目か

        '''
        # 連休日数
        consecutive_holidays = 0
        # 連休何日目か
        holiday_count = 0
        # 3日以内の営業日を休みにした場合の連休日数
        connect_consecutive_holidays = 0
        # 3日以内の営業日を休みにした場合の連休何日目か
        connect_holiday_count = 0

        # 今日の日付
        current_date = now.date()
        # 今日の休日フラグ
        today_flag = False
        # 連休フラグ
        consecutive_flag = True
        # 平日カウンター
        weekday_conut = 0

        # 今日の日付以前の休日・祝日チェック
        while True:
            # 休日あるいは祝日か
            if str(current_date) in holiday_list or current_date.weekday() >= 5:
                if consecutive_flag:
                    consecutive_holidays += 1
                    holiday_count += 1
                    today_flag = True
                weekday_conut = 0
            else:
                consecutive_flag = False
                weekday_conut += 1
            connect_consecutive_holidays += 1
            connect_holiday_count += 1

            # 4日以上平日が続いたら探索終了
            if weekday_conut == 4:
                connect_consecutive_holidays -= 4
                connect_holiday_count -= 4
                break

            # 1日戻す
            current_date -= timedelta(days = 1)

        # 明日の日付
        feture_date = now.date() + timedelta(days = 1)
        # フラグ／カウンターリセット
        consecutive_flag = today_flag
        weekday_conut = 0

        # 明日の日付以降の休日・祝日チェック
        while True:
            # 休日あるいは祝日か
            if str(feture_date) in holiday_list or feture_date.weekday() >= 5:
                if consecutive_flag:
                    consecutive_holidays += 1  # 連休日数
                weekday_conut = 0
            else:
                consecutive_flag = False
                weekday_conut += 1
            connect_consecutive_holidays += 1 # 3連続連休日数

            if weekday_conut == 4:
                connect_consecutive_holidays -= 4 # 3連続連休日数
                break

            # 1日進める
            feture_date += timedelta(days = 1)

        return consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count

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

    def prediction_wait_time(self, df, type = 1):
        '''待ち時間の予想を行う'''

        # ランダムフォレスト
        if type == 1:
            # 学習したランダムフォレストのパイプラインを読み込む
            with open('./data/rf_trained_model.pkl', 'rb') as f:
                rf_pipeline = pickle.load(f)

            return rf_pipeline.predict(df).astype(int)[0]

        # 勾配ブースティング
        else:
            with open('./data/gb_trained_model.pkl', 'rb') as f:
                gb_pipeline = pickle.load(f)

            return gb_pipeline.predict(df).astype(int)[0]

m = Main()
m.main()