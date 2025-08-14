import requests


if __name__ == '__main__':
    # url = "http://103.118.254.151/proxy/set"
    url = "http://127.0.0.1:5000/status_update"
    header = {"content-type" : "application/json"}
    #
    json = {
        "pad_code":"123",
        "number_of_run": 1,
        "phone_number_counts": 1,
    }

    #
    re = requests.put(url, json=json, headers = header)
    #
    print(re.json())
