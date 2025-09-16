import requests


if __name__ == '__main__':
       url = "http://103.115.64.73:3000/proxy/set"
       header = {"content-type" : "application/json"}
       json = {
           "pad_code": "AC32010790283",
           "country_code": "ma"
       }
       re = requests.post(url, headers = header, json=json)
       print(re.json())
