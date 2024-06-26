import config
import csv
import html
import japanize_matplotlib # グラフ日本語表示に必要なので消さない
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import pickle
import requests
import time
import shutil
from holiday import Holiday
from log import Log
from datetime import datetime, timedelta, timezone
from store import Store

class Main(Holiday):
    def __init__(self):
        self.log = Log()
        self.store = Store()
        self.now = datetime.now(timezone.utc) + timedelta(hours = 9)
        self.gotenba_stop_time = -1
        self.holiday_flag = False

    def main(self):
        self.log.info('さわやか待ち時間更新スクリプト開始')

        self.log.info('祝日データの取得開始')
        holiday_list = self.get_holidays()
        if holiday_list == False:
            self.log.error('祝日データ取得に失敗したため処理を終了します')
            return False
        self.log.info('祝日データの取得終了')

        # 連休情報の補正
        holiday_list = self.correction_holidays(holiday_list)

        # 連休情報の計算
        consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count = self.calc_holidays(holiday_list)

        if holiday_count > 0:
            self.holiday_flag = True

        self.log.info('Meteo APIから今日の天気データを取得開始')
        weather_info = self.get_weather()
        if weather_info == False:
            self.log.error('天気データ取得に失敗したため処理を終了します')
            return False
        self.log.info('Meteo APIから今日の天気データを取得終了')

        self.log.info('学習済みモデルの読み込み開始')
        result = self.get_model()
        if result == False:
            return False
        self.log.info('学習済みモデルの読み込み終了')

        # 店舗ごとに画像URLを格納するリスト
        prediction_image_list = []

        # 店舗ごとに予測を行う
        for store_id in range(1, 35):
            # 待ち時間設定用
            before_wait_time = -1
            wait_time_list = []

            # 営業時間(受付開始時間・開店時間・閉店時間・オーダーストップの時間)を取得する
            reception_hours, opening_hours, closing_hours, order_stop_hours = self.store.get_business_hours(store_id, self.now, self.holiday_flag)

            # 営業時間から予測範囲の決定(受付開始時間~オーダーストップの時間まで)
            start_time = datetime.strptime(reception_hours, "%H:%M")
            end_time = datetime.strptime(order_stop_hours, "%H:%M")
            time_list = [start_time + timedelta(minutes = 10 * i) for i in range(int((end_time - start_time).total_seconds() // 600) + 1)]

            # 時間ごとに予測を行う
            for prediction_time in time_list:
                # 天気データを予測用のDataFrameに充てる
                prediction_data = self.mold_weather_info(weather_info, prediction_time.hour)

                # 足りないデータを埋めていく
                prediction_data['store_name'] = store_id
                #prediction_data['month'] = self.now.month # まだ1年分のデータがたまってないので使わない
                prediction_data['minute'] = prediction_time.minute
                prediction_data['weekday'] = self.now.weekday
                prediction_data['consecutive_holidays'] = consecutive_holidays
                prediction_data['holiday_count'] = holiday_count
                prediction_data['connect_consecutive_holidays'] = connect_consecutive_holidays
                prediction_data['connect_holiday_count'] = connect_holiday_count
                prediction_data['before_10min_wait_time'] = before_wait_time

                # 加工したデータを学習済みモデルにあて、予測を行う
                wait_time = self.prediction_wait_time(prediction_data)
                if wait_time == False:
                    wait_time = 0 # TODO 予測失敗時の対応を考える

                # 予測待機時間がマイナスの場合は0にする
                if wait_time < 0:
                    wait_time = 0

                wait_time_list.append(wait_time)
                before_wait_time = wait_time

            # 最後に謎に跳ね上がるので補正を加える TODO 暫定対応なのでどっかで直したい
            wait_time_list[-1] = wait_time_list[-3]
            wait_time_list[-2] = wait_time_list[-3]

            # 予測データから画像の作成
            image_name, image_path = self.create_prediction_image(wait_time_list, store_id, reception_hours, order_stop_hours)

            # 予測データの画像投稿,URL取得
            image_url, image_id = self.post_gyazo_api(image_name, image_path)
            if image_url == False:
                self.log.error(f'store_id: {store_id}の店舗の画像投稿に失敗したためこの店舗の予測投稿はスキップします')
                continue

            # 予測データの格納
            prediction_image_list.append({'store_id': store_id, 'image_url': image_url, 'image_id': image_id})

        # 予測データから記事のHTMLを作成する
        article_html = self.create_html(prediction_image_list)

        # はてなブログの記事を更新する
        result = self.post_hatena(html.escape(article_html))
        if result == False:
            self.log.error('はてなブログへの投稿に失敗しました')
            return False

        # imgフォルダの画像を全部消す
        result = self.delete_image_folder()

        # Gyazoに上げた使わなくなった予測画像の削除
        result = self.delete_gyazo_image()

        # Gyazoに上げた画像IDをCSVに記録
        result = self.record_image_id(prediction_image_list)

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
        try:
            with open(os.path.join('.', 'data', 'rf_trained_model.pkl'), 'rb') as f:
                self.rf_pipeline = pickle.load(f)

            with open(os.path.join('.', 'data', 'gb_trained_model.pkl'), 'rb') as f:
                self.gb_pipeline = pickle.load(f)
        except Exception as e:
            self.log.error(f'学習済みモデルの取得に失敗しました\n{e}')
            return False

        return True

    def prediction_wait_time(self, df, type = 1):
        '''待ち時間の予測を行う'''

        try:
            # ランダムフォレスト
            if type == 1:
                return self.rf_pipeline.predict(df).astype(int)[0]

            # 勾配ブースティング
            else:
                return self.gb_pipeline.predict(df).astype(int)[0]
        except Exception as e:
            self.log.error('待ち時間の予測に失敗しました')
            return False

    def create_prediction_image(self, wait_time_list, store_id, start_time, end_time):
        '''
        予測データをグラフ化・画像化する

        Args:
            wait_time_list(list[int,int...]): 待ち時間データ
            store_id(int): 店舗ID
            start_time(str,HH:MM): 入店受付開始時間
            end_time(str,HH:MM): オーダーストップ時間

        Returns:
            file_name(str): 画像ファイル名
            file_path(str): 画像ファイルパス
        '''

        # 画像ファイル名・ファイルパス作成
        file_name = f'{self.now.strftime("%Y%m%d")}_{store_id}'
        file_path = f'./image/{file_name}.png'

        # 横軸(時刻)のリストを作成
        start_time = datetime.strptime(start_time, '%H:%M')
        end_time = datetime.strptime(end_time, '%H:%M')
        # 営業時間を10分ごとに分割した場合に何個に分けられるか
        time_intervals = int((end_time - start_time).seconds / 600)
        # 10分ごとの時間
        times = [start_time + timedelta(minutes=10 * i) for i in range(time_intervals + 1)]

        # グラフを描画
        fig, ax = plt.subplots(figsize=(10, 6))

        # 御殿場プレミアム・アウトレット店以外
        if store_id != 28:
            ax.plot(times, wait_time_list, linestyle='-', color='b', label='待ち時間')
        # 御殿場プレミアム・アウトレット店
        else:
            # 開店時間まで9:00から何分か(9:00ベースに受付中止時刻の予想をしている)
            correction_minutes = (start_time - datetime.strptime('09:00', '%H:%M')).total_seconds() / 60

            # 推定受付中止時刻を超えたらその時間で止まるように
            # -1.0016[係数] x (i * 10 + correction_minutes)[9:00からの経過分数] + 586.91(切片)
            stop_border = [-1.0016 * (i * 10 + correction_minutes) + 586.91 for i in range(len(wait_time_list))]

            for i in range(len(wait_time_list)):
                if wait_time_list[i] > stop_border[i]:
                    self.gotenba_stop_time = (start_time + timedelta(minutes = i * 10)).strftime('%H:%M')
                    wait_time_list[i:] = [wait_time_list[i]] * (len(wait_time_list) - i)
                    break
            ax.plot(times, wait_time_list, linestyle='-', color='b', label='待ち時間')

            # 受付中止グラフの追加
            #x = np.linspace(0, len(times)-1, 400)  # インデックスの範囲でxを作成
            # -1.0016[係数] x (x * 営業時間の秒数 / 60(分変換) / 400(分割) + correction_minutes)[9:00からの経過分数] + 586.91(切片)
            y = np.array([-1.0016 * ((x * (end_time - start_time).seconds / 24000) + correction_minutes) + 586.91 for x in range(400)])

            # インデックスの範囲を時刻に変換
            times_x = [start_time + timedelta(minutes=10 * i * (len(times)-1) / 399) for i in range(400)]

            # 線形関数をプロット
            ax.plot(times_x, y, label='y = -1.0016x + 586.91', color='r')

            # 線より上の領域を赤色で塗りつぶす
            ax.fill_between(times_x, y, y2=max(y), where=(y < max(y)), color='red', alpha=0.3)

            # 縦軸の描画範囲を受付中止グラフではなく予測時間に合わせる
            plt.ylim(min(wait_time_list) - 50, max(wait_time_list) + 20)

        # TODO 営業時間やオーダーストップの時間に縦線入れてわかりやすくしたいなぁ

        # 横軸のフォーマットを設定
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)

        # グラフのラベルとタイトル
        ax.set_xlabel('時刻')
        ax.set_ylabel('待ち時間(分)')
        ax.set_title(f'{self.store.get_store_name(store_id)}の待ち時間予測（{self.now.strftime("%Y/%m/%d")}）')

        # グリッド表示
        ax.grid(True)

        # 位置調整(グラフ下に空白追加)
        plt.subplots_adjust(bottom = 0.15)

        # 画像を保存
        plt.savefig(file_path)
        plt.close()

        return file_name, file_path

    def create_html(self, prediction_data):
        '''
        予測データの画像URL(と待ち時間)から記事のHTMLを作成する

        Args:
            prediction_data(dict): 予測データ
                store_id(int): 店舗に割り振ったID
                image_url(str): 1日の待ち時間の予測画像のURL
                (image_id(str): 画像に振られたID)

        Returns:
            article_html(str): 記事のHTML
        '''

        double_space = chr(32) + chr(32)

        article_html = f'''
静岡のハンバ―グレストランさわやかの非公式待ち時間予測AI(β版)です。{double_space}
まだまだ精度は高くないため、あくまで参考程度にご活用ください。{double_space}
<br>
最終更新：{self.now.strftime("%Y/%m/%d %H:%M")}
'''

        # 店舗ごとにHTMLの作成
        for data in prediction_data:
            store_id = data['store_id']

            # 見出し
            article_html += f'''<details>
<summary>{self.store.get_store_name(data['store_id'])}</summary>
'''

            # 営業時間・受付開始時間表示
            reception, opening, closing, order_stop = self.store.get_business_hours(store_id, self.now, self.holiday_flag)
            article_html += f'''
入店受付開始時間: {reception}{double_space}
営業時間: {opening}~{closing}（オーダーストップ: {order_stop}）{double_space}
'''
            # 予測グラフ
            article_html +=f'''
<img src="{data['image_url']}">{double_space}
'''
            # 御殿場プレミアム・アウトレット店の受付中止表示対応
            if store_id== 28:
                article_html += f'''
※赤枠内に待ち時間が到達すると、その日の受付は中止になる可能性が高いです。{double_space}
'''
                # グラフが赤枠内に到達する場合
                if self.gotenba_stop_time != -1:
                    article_html += f'''
本日の予測では{self.gotenba_stop_time}頃に受付中止になる見込みです。</details>{double_space}
'''
            else:
                article_html += '''
</details>
'''

        return article_html

    def record_image_id(self, prediction_data):
        '''
        Gyazoにアップロードした画像のIDをCSVに記録する

        Args:
            prediction_data(dict): 予測データ
                image_id(str): 画像に振られたID
                (store_id(int): 店舗に割り振ったID)
                (image_url(str): 1日の待ち時間の予測画像のURL)

        Returns:
            result(bool): 実行結果
        '''
        # ファイルパスの定義
        file_path = os.path.join('.', 'manage', 'image_id.csv')

        # timestumpのフォーマットを定義
        timestump = self.now.strftime('%Y%m%d%H%M')

        # ファイルが存在するか、存在して中身が空でないかをチェック
        file_exists = os.path.isfile(file_path)
        file_is_empty = file_exists and os.path.getsize(file_path) == 0

        # 書き込みモードの選択
        write_header = not file_exists or file_is_empty

        for data in prediction_data:
            image_id = data['image_id']

            # CSVファイルに追記
            with open(file_path, mode='a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                if write_header:
                    # ヘッダー行を書き込む
                    writer.writerow(['image_id', 'timestump'])
                    write_header = False
                # データ行を書き込む
                writer.writerow([image_id, timestump])

        return True

    def post_gyazo_api(self, image_name, image_path):
        '''
        Gyazo APIを用いて画像をアップロードする

        Args:
            image_name(str): 画像ファイル名
            image_path(str): 画像ファイルの相対パス

        Returns:
            image_url(str): アップロード画像のURL
        '''
        time.sleep(2)
        # ヘッダーの設定
        headers = {'Authorization': f'Bearer {config.GYAZO_ACCESS_TOKEN}'}

        # 画像のバイナリ変換
        with open(image_path, 'rb') as f:
            files = {'imagedata': f.read()}

        # リクエスト送信
        response = requests.post('https://upload.gyazo.com/api/upload', headers = headers, files = files, data = {'desc': image_name})

        # ステータスチェック
        if response.status_code != 200:
            self.log.error(f'Gyazo APIの画像アップロードでエラー レスポンスコード: {response.status_code}')
            return False, False

        # レスポンスデータ変換
        response_data = response.json()
        return response_data['url'], response_data['image_id']

    def post_hatena(self, content):
        '''
        はてなブログの記事の更新を行う

        Args:
            content(str) : 記事内容

        Returns:
            response(str): 結果
        '''

        xml = f'''<?xml version="1.0" encoding="utf-8"?>
                    <entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">
                        <title>さわやか待ち時間予測AI β版(ver.0.1)</title>
                            <author>
                                <name>name</name>
                            </author>
                        <content type="text/markdown">{content}</content>
                        <updated>2000-01-01T00:00:00</updated>
                        <category term="さわやか" />
                        <category term="ツール" />
                        <app:control>
                            <app:draft>no</app:draft>
                        </app:control>
                    </entry>'''.encode('UTF-8')
        response = requests.put(f'{config.URL}/entry/{config.ARTICLE_ID}', auth = (config.ID, config.API_KEY), data = xml)

        self.log.info(f'レスポンスコードは~~~{response.status_code}!!!')

        # ステータスチェック TODO 200か201かチェック
        #if response.status_code != 200:
        #    self.log.error(f'はてなへの記事投稿処理でエラー レスポンスコード: {response.status_code}')
        #    return False

        return response

    def delete_image_folder(self):
        '''imageフォルダに作成した画像をすべて削除する'''
        image_folder = os.path.join('.', 'image')

        # imageフォルダが存在するか確認
        if not os.path.exists(image_folder):
            self.log.warning('imageフォルダが存在しません')
            return False

        # imageフォルダ内のすべてのファイルとフォルダをリストアップ
        files = os.listdir(image_folder)

        for file_name in files:
            file_path = os.path.join(image_folder, file_name)
            # .gitkeepファイルをスキップ
            if file_name == '.gitkeep':
                continue
            # ファイルかディレクトリかを確認
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                # ディレクトリの場合はディレクトリごと削除（再帰的に削除）
                shutil.rmtree(file_path)

    def delete_gyazo_image(self):
        '''
        Gyazoにアップロードした画像でもう使わないものを削除する

        Returns:
            result(bool): 実行結果
        '''
        file_path = os.path.join('.', 'manage', 'image_id.csv')

        # CSVファイルの存在を確認
        if not os.path.isfile(file_path):
            self.log.warning('Gyazo画像ID記録用のCSVが見つかりません')
            return False

        # CSVファイルを読み込み
        with open(file_path, mode='r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            delete_counter = 0

            for row in reader:
                image_id = row['image_id']

                # 同一時分(=同一プロセスで追加された画像)でないもののみAPIで削除する
                if row['timestump'] != self.now.strftime('%Y%m%d%H%M'):
                    # DeleteのGyazo API呼び出し
                    result = self.delete_gyazo_api(image_id)
                    if result == False:
                        continue

                    # 削除したIDのレコードをCSVから削除する
                    result = self.delete_gyazo_id(image_id)
                    if result == False:
                        self.log.info(f'CSV操作に失敗したため、手動でimage_idをCSVから消してください\nimage_id: {image_id}')
                        continue

                    delete_counter += 1

            self.log.info(f'{delete_counter}枚の写真をGyazoから削除しました')

        return True

    def delete_gyazo_api(self, image_id):
        '''
        Gyazo APIを用いて過去の画像を削除する

        Args:
            image_id(str): 画像ID

        Returns:
            result(bool): 実行結果
        '''
        time.sleep(1)

        headers = {'Authorization': f'Bearer {config.GYAZO_ACCESS_TOKEN}'}

        try:
            response = requests.delete(f'https://api.gyazo.com/api/images/{image_id}', headers = headers)
        except Exception as e:
            self.log.error(f'Gyazo APIの画像削除でエラー\n{e}')

        # ステータスチェック
        if response.status_code != 200:
            self.log.error(f'Gyazo APIの画像削除でエラー レスポンスコード: {response.status_code}')
            return False

        return True

    def delete_gyazo_id(self, image_id):
        '''
        Gyazoから削除した画像IDのレコードをCSVから削除する

        Args:
            image_id(str): 画像ID

        Returns:
            result(bool): 実行結果
        '''
        try:
            csv_path = os.path.join('.', 'manage', 'image_id.csv')
            rows_to_keep = []

            # CSVファイルを読み込む
            with open(csv_path, 'r', newline = '', encoding = 'utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    # 最左列の値が引数のimage_idと一致しない場合に行を保持する
                    if row[0] != image_id:
                        rows_to_keep.append(row)

            # 新しい内容をファイルに書き込む
            with open(csv_path, 'w', newline = '', encoding = 'utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(rows_to_keep)
        except Exception as e:
            self.log.error(f'Gyazoから削除した画像IDのレコードをCSVから除去するのに失敗\n{e}')
            return False

        return True


if __name__ == '__main__':
    m = Main()
    m.main()
