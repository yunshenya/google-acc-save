import requests


if __name__ == '__main__':
   # for i in range(999, 1100):
       url = "http://127.0.0.1:5000/proxy/set"
       # url = f"http://103.118.254.151/accounts/{i}"
       # url = "http://127.0.0.1:5000/status_update"
       header = {"content-type" : "application/json"}
       #
       json = {
           "pad_code": "123",
           "country_code": "dz"
       }

       #
       re = requests.post(url, headers = header, json=json)
       #
       print(re.json())
