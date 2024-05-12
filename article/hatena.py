import config
import requests
from datetime import datetime

def hatena_entry(content):
    '''
    記事の更新を行う

    Args:
      title (str):
      content(str) : 記事内容
      categorys (List[str]):
      updated (str): %Y-%m-%dT%H:%M:%S
      draft (bool):

    Returns:
      str: xml
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
    r = requests.put(f'{config.URL}/entry/{config.ARTICLE_ID}', auth = (config.ID, config.API_KEY), data = xml)
    return r


if __name__ == '__main__':
    content = f'最終更新時間：{datetime.now()}\nAPIから投稿'
    #print(content)
    #exit()
    result = hatena_entry(content)
    print(f'ステータスコード: {result.status_code} ,結果: {result.content}')