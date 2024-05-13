import json
import config
import requests

headers = {
    'authorization': f'Client-ID {config.IMGUR_CLIENT_ID}',
}
files = {
    'image': (open('image/fuga.png', 'rb')),
}

r = requests.post('https://api.imgur.com/3/upload', headers=headers, files=files)

print(json.loads(r.text)['data']['link'])