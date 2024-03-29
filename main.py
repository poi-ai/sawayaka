import csv
import log
import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

###### 待ち時間情報取得／CSV記録用 ######

class Main():
    def __init__(self):
        self.log = log.Log()

    def main(self):
        self.log.info('さわやか待ち時間記録スクリプト開始')
        # Open Meteo APIから天候情報の取得
        weather_info = self.get_weather()
        if weather_info == False:
            return

        # さわやかのHPから待ち時間ページのHTML取得
        soup = self.get_sawayaka_hp()
        if soup == False:
            return

        # 現在時刻を取得
        now = datetime.utcnow() + timedelta(hours = 9)

        # Holidays JP APIから祝日一覧を取得
        holiday_list = self.get_holidays()

        # 連休情報の補正
        holiday_list = self.correction_holidays(holiday_list, now)

        # 連休情報の計算
        consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count = self.calc_holidays(holiday_list, now)

        # 各店舗情報をリストに格納
        store_list = []
        for store in soup.find_all('div', class_ = 'shop_info'):
            store_info = {}
            store_info['store_name'] = store.find('span', class_ = 'name').text                                      # 店舗名
            store_info['wait_time'] = store.find('p', 'time').find('span', class_ = 'num').text.replace('-', '-1')   # 待ち時間(分)
            store_info['wait_count'] = store.find('p', 'set').find('span', class_ = 'num').text.replace('-', '-1')   # 待ち組数(組)
            store_info['temperature'] = weather_info['temperature_2m']                                               # 気温
            store_info['relative_humidity'] = weather_info['relative_humidity_2m']                                   # 湿度(%)
            store_info['precipitation'] = weather_info['precipitation']                                              # 降水量(雨+雪)
            store_info['rain'] = weather_info['rain']                                                                # 降雨量
            store_info['snowfall'] = weather_info['snowfall']                                                        # 降雪量
            store_info['weather_code'] = weather_info['weather_code']                                                # 天気コード
            store_info['month'] = now.month                                                                          # 月
            store_info['day'] = now.day                                                                              # 日(管理用で学習には使わない予定)
            store_info['hour'] = now.hour                                                                            # 時
            store_info['minute'] = now.minute                                                                        # 分(管理用で学習には使わない)
            store_info['weekday'] = now.weekday()                                                                    # 曜日フラグ(月～日)
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

    def output_csv(self, data):
        '''
        dict型のデータをCSVへ出力する

        Args:
            data(list[dict{},dict{},...]): dictで保持されているデータのlist

        '''

        # 格納先のCSVのパスを指定
        file_path = './data/sawayaka_data.csv'

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