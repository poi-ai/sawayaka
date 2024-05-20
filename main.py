import csv
import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from holiday import Holiday
from log import Log
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from store import Store

###### 待ち時間情報取得／CSV記録用 ######

class Main(Holiday):
    def __init__(self):
        self.log = Log()
        self.store = Store()

    def main(self):
        self.log.info('さわやか待ち時間記録スクリプト開始')
        # Open Meteo APIから天候情報の取得
        weather_info = self.get_weather()
        if weather_info == False:
            return

        # さわやかのHPから待ち時間ページのHTML取得
        soup = self.get_sawayaka_hp()
        if soup == False:
            self.log.info('再取得します')
            time.sleep(10)
            soup = self.get_sawayaka_hp()
            if soup == False:
                return

        # 現在時刻を取得
        self.now = datetime.now(timezone.utc) + timedelta(hours = 9)

        # Holidays JP APIから祝日一覧を取得
        holiday_list = self.get_holidays()

        # 連休情報の補正
        holiday_list = self.correction_holidays(holiday_list)

        # 連休情報の計算
        consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count = self.calc_holidays(holiday_list)

        # 各店舗情報をリストに格納
        store_list = []
        for store in soup.find_all('div', class_ = 'shop_info'):
            # データ量圧縮のため、店舗名を独自に割り振った店舗IDに変換
            store_id = self.store.get_store_id(store.find('span', class_ = 'name').text)

            store_info = {}
            store_info['store_name'] = store_id                                                                      # 店舗名ごとに独自に振り分けた店舗ID
            store_info['wait_time'] = store.find('p', 'time').find('span', class_ = 'num').text.replace('-', '-1')   # 待ち時間(分)
            store_info['wait_count'] = store.find('p', 'set').find('span', class_ = 'num').text.replace('-', '-1')   # 待ち組数(組)
            store_info['temperature'] = weather_info['temperature_2m']                                               # 気温
            store_info['relative_humidity'] = weather_info['relative_humidity_2m']                                   # 湿度(%)
            store_info['precipitation'] = weather_info['precipitation']                                              # 降水量(雨+雪)
            store_info['rain'] = weather_info['rain']                                                                # 降雨量
            store_info['snowfall'] = weather_info['snowfall']                                                        # 降雪量
            store_info['weather_code'] = weather_info['weather_code']                                                # 天気コード
            store_info['month'] = self.now.month                                                                          # 月
            store_info['day'] = self.now.day                                                                              # 日(管理用で学習には使わない予定)
            store_info['hour'] = self.now.hour                                                                            # 時
            store_info['minute'] = self.now.minute                                                                        # 分(管理用で学習には使わない)
            store_info['weekday'] = self.now.weekday()                                                                    # 曜日フラグ(月～日)
            store_info['consecutive_holidays'] = consecutive_holidays                                                # 連休日数
            store_info['holiday_count'] = holiday_count                                                              # 連休何日目
            store_info['connect_consecutive_holidays'] = connect_consecutive_holidays                                # 3日以内の営業日を休みにした場合の連休日数
            store_info['connect_holiday_count'] = connect_holiday_count                                              # 3日以内の営業日を休みにした場合の連休何日目

            store_list.append(store_info)

        # 結果のCSV出力
        self.output_csv(store_list)

        self.log.info('さわやか待ち時間記録スクリプト終了')

        return True

    def get_weather(self):
        '''
        静岡県庁の現在の天候情報をOpen Meteo APIから取得する

        Returns:
            weather_info(dict): 天候情報
                temperature_2m(float): 気温(℃)
                relative_humidity_2m(int): 湿度(%)
                precipitation(float): 降水量(mm) [降雨量+降雪量]
                rain(float): 降雨量(mm)
                snowfall(float): 降雪量(cm)
                weather_code(int): 天気コード
                    https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
        '''
        # API呼び出し
        weather_api_url = 'https://api.open-meteo.com/v1/forecast'
        weather_api_params = {
            'latitude': 34.976944,
            'longitude': 138.383056,
            'current': 'temperature_2m,relative_humidity_2m,precipitation,rain,snowfall,weather_code',
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

        weather_info = r.json()['current']

        if len(weather_info) == 0:
            self.log.error(f'天候情報取得APIエラー レスポンス情報が空')
            return False

        return weather_info

    def get_sawayaka_hp(self):
        '''
        さわやかのHPから現在の待ち時間を取得する

        Returns:
            soup(bs4.BeautifulSoup): 待ち時間ページのHTML

        '''
        try:
            # ヘッドレスでブラウザ起動
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options = chrome_options)

            # さわやかのページ情報を取得
            driver.get('https://www.genkotsu-hb.com/shop/')

            # JSが待ち時間管理APIを叩きに行くのを待つ
            time.sleep(5)
            # 5秒待ってもまだ読み込まれていなかったらさらに待機
            driver.implicitly_wait(10)

            # APIから取得した値をHTMLに反映
            html_after_execution = driver.page_source

            # 反映されたHTMLを取得、操作できるbs4型に
            soup = BeautifulSoup(html_after_execution, 'html.parser')

            if len(soup) == 0:
                self.log.error('さわやかHPから待ち時間情報の取得に失敗 レスポンスが空')
                return False
        except Exception as e:
            self.log.error(f'さわやかHPから待ち時間情報の取得に失敗\n{e}')
            return False

        return soup

    def output_csv(self, data):
        '''
        dict型のデータをCSVへ出力する

        Args:
            data(list[dict{},dict{},...]): dictで保持されているデータのlist

        '''

        # 格納先のCSVのパスを指定
        file_path = os.path.join('.', 'data', 'sawayaka_data.csv')

        # 既に引数のファイルが存在する場合は追記、そうでない場合は上書き（新規作成）
        mode = 'a' if os.path.exists(file_path) else 'w'

        with open(file_path, mode, encoding = 'UTF-8', newline = '') as csvfile:
            fieldnames = data[0].keys() if data else []
            writer = csv.DictWriter(csvfile, fieldnames = fieldnames)

            if mode == 'w':
                writer.writeheader()

            for row in data:
                writer.writerow(row)

        return True

if __name__ == '__main__':
    m = Main()
    m.main()