import requests
resp = requests.get('http://127.0.0.1:5001/questions')
print('status', resp.status_code)
print(resp.json())
