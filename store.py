from datetime import timedelta, timezone, datetime

class Store:
    def __init__(self):
        self.store_info = {
            '浜松篠ケ瀬店': 1,
            'イオンモール浜松市野店': 2,
            '浜松白羽店': 3,
            '浜松遠鉄店': 4,
            '浜松和合店': 5,
            '浜松有玉店': 6,
            '浜松富塚店': 7,
            '浜松鴨江店': 8,
            '浜松高塚店': 9,
            '浜松高丘店': 10,
            '浜北店': 11,
            '細江本店': 12,
            '湖西浜名湖店': 13,
            '菊川本店': 14,
            '掛川本店': 15,
            '掛川インター店': 16,
            '袋井本店': 17,
            '磐田本店': 18,
            '豊田店': 19,
            '新静岡セノバ店': 20,
            '静岡瀬名川店': 21,
            '静岡池田店': 22,
            '静岡インター店': 23,
            '焼津店': 24,
            '藤枝築地店': 25,
            '島田店': 26,
            '吉田店': 27,
            '御殿場プレミアム・アウトレット店': 28,
            '御殿場インター店': 29,
            '函南店': 30,
            '長泉店': 31,
            '沼津学園通り店': 32,
            '富士鷹岡店': 33,
            '富士錦店': 34
        }
        self.id_to_store = {v: k for k, v in self.store_info.items()}

    def get_store_id(self, store_name):
        '''店舗名を独自に割り振った店舗IDへ変換する'''
        if store_name in self.store_info:
            return self.store_info[store_name]
        else:
            return store_name

    def get_store_name(self, store_id):
        '''店舗IDから店舗名を取得する'''
        if store_id in self.id_to_store:
            return self.id_to_store[store_id]
        else:
            return store_id

    def get_business_hours(self, store_id, now, holiday_flag):
        '''
        店舗IDから営業時間を取得する

        Args:
            store_id(int): 店舗ID
            now(datetime): 現在時刻
            holiday_flag(bool): 土日祝日か

        Returns:
            opening_hours(str,HHMM): 開店時間
            closing_hours(str,HHMM): 閉店時間
            order_stop_hours(str,HHMM): オーダーストップ時間
        '''
        # イオンモール浜松市野店/新静岡セノバ店
        if store_id == 2:
            if holiday_flag:
                return '10:45', '21:00', '20:00'
            else:
                return '11:00', '21:00', '20:00'

        # 浜松遠鉄店
        elif store_id == 4:
            if holiday_flag:
                return '10:45', '22:00', '21:00'
            else:
                return '11:00', '22:00', '21:00'

        # イオンモール浜松市野店/新静岡セノバ店
        elif store_id == 20:
            return '11:00', '21:00', '20:00'

        # 御殿場プレミアム・アウトレット店
        elif store_id == 28:
            if 3 <= now.month <= 11:
                return '10:30', '20:00', '19:00'
            else:
                return '10:30', '19:00', '18:00'

        # 御殿場インター店
        elif store_id == 29:
            if holiday_flag:
                return '10:30', '23:00', '22:00'
            else:
                return '10:45', '23:00', '22:00'

        # その他店舗
        else:
            if holiday_flag:
                return '10:45', '23:00', '22:00'
            else:
                return '11:00', '23:00', '22:00'

    def get_closing_day(self, store_id):
        '''
        定休日を取得する ※年末までは定休日ないから優先度は低

        全店（浜松遠鉄店、イオンモール浜松市野店、御殿場プレミアム・アウトレット店除く）
        ※定休日 12/31,1/1

        イオンモール浜松市野店 store_id=2、浜松遠鉄店 store_id=4
        ※定休日 1/1

        御殿場プレミアム・アウトレット店 store_id=28
        休みなし？
        '''
        pass
