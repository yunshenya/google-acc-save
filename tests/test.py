import requests


if __name__ == '__main__':
    url = "http://localhost:4000/status_update"
    header = {"content-type" : "application/json"}
    json = {
        "pad_code": "AC32010800443",
        "phone_number_counts": 1
    }
    re = requests.post(url, headers = header, json=json)
    print(re.text)