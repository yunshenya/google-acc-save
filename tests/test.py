import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:4000/create_accounts"
    header = {"content-type" : "application/json"}
    json = {
        "account": "sdfsswsadef",
        "password": "dsfrg",
        "pad_code": "ACP250423RNNLK3X"
    }
    re = requests.post(url, headers = header, json = json)
    print(re.json())