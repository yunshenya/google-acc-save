import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:4000/status"
    header = {"content-type" : "application/json"}
    json_data = {
        "pad_code": "test",
        "type":0 #1表示遇到错误 0表示其他错误
    }
    re = requests.post(url, headers = header, json=json_data)
    print(re.json())