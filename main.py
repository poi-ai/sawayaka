import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

###### 待ち時間情報取得／CSV記録用 ######

class Main():

    def main(self):

        # ヘッドレスでブラウザ実行
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(options=chrome_options)

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

        # 現在時刻を取得
        now = datetime.utcnow() + timedelta(hours = 9)

        # TODO 天気API
        # https://api.open-meteo.com/v1/forecast?latitude=34.976944&longitude=138.383056&current=temperature_2m,precipitation,rain,snowfall,weather_code&hourly=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Asia%2FTokyo&forecast_days=1

        # TODO 連休フラグ
        # TODO 連休間フラグ(つなげる人とか)

        # 各店舗情報をリストに格納
        store_list = []
        for store in soup.find_all('div', class_ = 'shop_info'):
            store_info = {}
            store_info['store_name'] = store.find('span', class_ = 'name').text
            store_info['wait_time'] = store.find('p', 'time').find('span', class_ = 'num').text
            store_info['wait_count'] = store.find('p', 'set').find('span', class_ = 'num').text
            #store_info['temperature_2m'] = weather_info['temperature_2m']
            #store_info['weather_code'] = weather_info['weather_code']

            store_list.append(store_info)

        print(store_list)

    def weather(self):
        '''
        静岡県庁の現在の天候情報をOpen Meteo APIから取得する

        Returns:
            weather_info(dict): 天候情報
                temperature_2m(float): 気温(℃)
                relative_humidity_2m(int): 湿度(%)
                precipitation(float): 降水量(mm) [降雨量+降雪量]
                rain(float): 降雨量(mm)
                snowfail(float): 降雪量(cm)
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

        r = requests.get(weather_api_url, params = weather_api_params)
        weather_info = r.json()

        if len(weather_info) == 0:
            return False
        


# TODO 精度を上げるために別ファイルで10分前、30分前、1時間前のデータも入れる


if __name__ == '__main__':
    m = Main()
    m.weather()