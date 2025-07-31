import requests

if __name__ == '__main__':
    url = "http://103.118.254.151/proxy/set"

    header = {"content-type" : "application/json"}

    json = {
        "country_code": "uy"
    }

    re = requests.post(url, json=json, headers = header)

    print(re.json())