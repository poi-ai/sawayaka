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
