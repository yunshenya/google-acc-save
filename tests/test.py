import requests


if __name__ == '__main__':
    # url = "http://103.118.254.151/proxy/set"
    url = "http://127.0.0.1:5000/callback"
    header = {"content-type" : "application/json"}
    #
    json = {
        "taskBusinessType": 1124,
        "packageName": "com.quark.browser",
        "padCode": "AC22030022001",
        "taskId": 10618,
        "taskStatus": -1
    }

    #
    re = requests.post(url, json=json, headers = header)
    #
    print(re.json())
