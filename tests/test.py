import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:5000/status_update"
    header = {"content-type" : "application/json"}
    #
    json = {
       "pad_code": "123",
        "current_status": "test"
    }

    #
    re = requests.put(url, json=json, headers = header)
    #
    print(re.json())
