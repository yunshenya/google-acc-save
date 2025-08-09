import requests


if __name__ == '__main__':
    # url = "http://103.118.254.151/proxy/set"
    url = "http://127.0.0.1:5000/proxy/set"
    #
    header = {"content-type" : "application/json"}
    #
    json = {
        "country_code": "om"
    }
    #
    re = requests.post(url, json=json, headers = header)
    #
    print(re.json())