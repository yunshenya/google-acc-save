import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:4000/proxy"
    header = {"content-type" : "application/json"}
    json_data = {
        "pad_code": "test",
    }
    re = requests.post(url, headers = header, json=json_data)
    print(re.json())