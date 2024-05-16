import requests
from datetime import datetime, timedelta, timezone

class Holiday():
    '''休日関連の共通処理'''
    def get_holidays(self):

        # 2030年までは列挙したデータを返す(メモリ削減)
        if int(self.now.strftime('%Y')) <= 2030:
            return {
                '2024-01-01','元日',
                '2024-01-08','成人の日',
                '2024-02-11','建国記念の日',
                '2024-02-12','振替休日',
                '2024-02-23','天皇誕生日',
                '2024-03-20','春分の日',
                '2024-04-29','昭和の日',
                '2024-05-03','憲法記念日',
                '2024-05-04','みどりの日',
                '2024-05-05','こどもの日',
                '2024-05-06','振替休日',
                '2024-07-15','海の日',
                '2024-08-11','山の日',
                '2024-08-12','振替休日',
                '2024-09-16','敬老の日',
                '2024-09-22','秋分の日',
                '2024-09-23','振替休日',
                '2024-10-14','スポーツの日',
                '2024-11-03','文化の日',
                '2024-11-04','振替休日',
                '2024-11-23','勤労感謝の日',
                '2025-01-01','元日',
                '2025-01-13','成人の日',
                '2025-02-11','建国記念の日',
                '2025-02-23','天皇誕生日',
                '2025-02-24','振替休日',
                '2025-03-20','春分の日',
                '2025-04-29','昭和の日',
                '2025-05-03','憲法記念日',
                '2025-05-04','みどりの日',
                '2025-05-05','こどもの日',
                '2025-05-06','振替休日',
                '2025-07-21','海の日',
                '2025-08-11','山の日',
                '2025-09-15','敬老の日',
                '2025-09-23','秋分の日',
                '2025-10-13','スポーツの日',
                '2025-11-03','文化の日',
                '2025-11-23','勤労感謝の日',
                '2025-11-24','振替休日',
                '2026-01-01','元日',
                '2026-01-12','成人の日',
                '2026-02-11','建国記念の日',
                '2026-02-23','天皇誕生日',
                '2026-03-20','春分の日',
                '2026-04-29','昭和の日',
                '2026-05-03','憲法記念日',
                '2026-05-04','みどりの日',
                '2026-05-05','こどもの日',
                '2026-05-06','振替休日',
                '2026-07-20','海の日',
                '2026-08-11','山の日',
                '2026-09-21','敬老の日',
                '2026-09-22','国民の休日',
                '2026-09-23','秋分の日',
                '2026-10-12','スポーツの日',
                '2026-11-03','文化の日',
                '2026-11-23','勤労感謝の日',
                '2027-01-01','元日',
                '2027-01-11','成人の日',
                '2027-02-11','建国記念の日',
                '2027-02-23','天皇誕生日',
                '2027-03-21','春分の日',
                '2027-03-22','振替休日',
                '2027-04-29','昭和の日',
                '2027-05-03','憲法記念日',
                '2027-05-04','みどりの日',
                '2027-05-05','こどもの日',
                '2027-07-19','海の日',
                '2027-08-11','山の日',
                '2027-09-20','敬老の日',
                '2027-09-23','秋分の日',
                '2027-10-11','スポーツの日',
                '2027-11-03','文化の日',
                '2027-11-23','勤労感謝の日',
                '2028-01-01','元日',
                '2028-01-10','成人の日',
                '2028-02-11','建国記念の日',
                '2028-02-23','天皇誕生日',
                '2028-03-20','春分の日',
                '2028-04-29','昭和の日',
                '2028-05-03','憲法記念日',
                '2028-05-04','みどりの日',
                '2028-05-05','こどもの日',
                '2028-07-17','海の日',
                '2028-08-11','山の日',
                '2028-09-18','敬老の日',
                '2028-09-22','秋分の日',
                '2028-10-09','スポーツの日',
                '2028-11-03','文化の日',
                '2028-11-23','勤労感謝の日',
                '2029-01-01','元日',
                '2029-01-08','成人の日',
                '2029-02-11','建国記念の日',
                '2029-02-12','振替休日',
                '2029-02-23','天皇誕生日',
                '2029-03-20','春分の日',
                '2029-04-29','昭和の日',
                '2029-04-30','振替休日',
                '2029-05-03','憲法記念日',
                '2029-05-04','みどりの日',
                '2029-05-05','こどもの日',
                '2029-07-16','海の日',
                '2029-08-11','山の日',
                '2029-09-17','敬老の日',
                '2029-09-23','秋分の日',
                '2029-09-24','振替休日',
                '2029-10-08','スポーツの日',
                '2029-11-03','文化の日',
                '2029-11-23','勤労感謝の日',
                '2030-01-01','元日',
                '2030-01-14','成人の日',
                '2030-02-11','建国記念の日',
                '2030-02-23','天皇誕生日',
                '2030-03-20','春分の日',
                '2030-04-29','昭和の日',
                '2030-05-03','憲法記念日',
                '2030-05-04','みどりの日',
                '2030-05-05','こどもの日',
                '2030-05-06','振替休日',
                '2030-07-15','海の日',
                '2030-08-11','山の日',
                '2030-08-12','振替休日',
                '2030-09-16','敬老の日',
                '2030-09-23','秋分の日',
                '2030-10-14','スポーツの日',
                '2030-11-03','文化の日',
                '2030-11-04','振替休日',
                '2030-11-23','勤労感謝の日'
            }

        # 2031年以降はAPIから取得
        else:
            return self.get_holidays_api()


    def get_holidays_api(self):
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

    def correction_holidays(self, holiday_list):
        '''
        祝日ではないが休みを取る人が多い日付を祝日リストに追加する
        (年末年始・お盆の追加)

        Args:
            holiday_list(dict): 実行日の昨年～来年までの祝日一覧

        Returns:
            holiday_list(dict): 修正後の祝日一覧

        '''
        now = self.now

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

    def calc_holidays(self, holiday_list):
        '''
        連休日数・連休何日目かを計算する

        Args:
            holiday_list(dict): 実行日の昨年～来年までの祝日一覧

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
        current_date = self.now.date()
        # 今日の休日フラグ
        today_flag = False
        # 連休フラグ
        consecutive_flag = True
        # 平日カウンター
        weekday_count = 0

        # 今日の日付以前の休日・祝日チェック
        while True:
            # 休日あるいは祝日か
            if str(current_date) in holiday_list or current_date.weekday() >= 5:
                if consecutive_flag:
                    consecutive_holidays += 1
                    holiday_count += 1
                    today_flag = True
                weekday_count = 0
            else:
                consecutive_flag = False
                weekday_count += 1
            connect_consecutive_holidays += 1
            connect_holiday_count += 1

            # 4日以上平日が続いたら探索終了
            if weekday_count == 4:
                connect_consecutive_holidays -= 4
                connect_holiday_count -= 4
                break

            # 1日戻す
            current_date -= timedelta(days = 1)

        # 明日の日付
        tomorrow_date = self.now.date() + timedelta(days = 1)
        # フラグ／カウンターリセット
        consecutive_flag = today_flag
        weekday_count = 0

        # 明日の日付以降の休日・祝日チェック
        while True:
            # 休日あるいは祝日か
            if str(tomorrow_date) in holiday_list or tomorrow_date.weekday() >= 5:
                if consecutive_flag:
                    consecutive_holidays += 1  # 連休日数
                weekday_count = 0
            else:
                consecutive_flag = False
                weekday_count += 1
            connect_consecutive_holidays += 1 # 3連続連休日数

            if weekday_count == 4:
                connect_consecutive_holidays -= 4 # 3連続連休日数
                break

            # 1日進める
            tomorrow_date += timedelta(days = 1)

        return consecutive_holidays, holiday_count, connect_consecutive_holidays, connect_holiday_count