import requests


if __name__ == '__main__':
    # url = "http://103.118.254.151/proxy/set"
    url = "http://127.0.0.1:5000/proxy/set"
    ur2 = "http://127.0.0.1:5000/proxy"
    #
    header = {"content-type" : "application/json"}
    #
    json = {
        "country_code": "tw"
    }
    #
    re = requests.post(url, json=json, headers = header)
    #
    print(re.json())

    pt = requests.get(ur2)
    print(pt.json())