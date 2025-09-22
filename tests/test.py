import requests


if __name__ == '__main__':
       url = "http://localhost:4000/proxy"
       header = {"content-type" : "application/json"}
       json = {
           "pad_code": "AC32010800443"
       }
       re = requests.post(url, headers = header, json=json)
       print(re.text)
