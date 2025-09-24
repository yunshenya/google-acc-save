import requests


if __name__ == '__main__':
       url = "http://127.0.0.1:4000/create_accounts"
       header = {"content-type" : "application/json"}
       json = {
           "for_email": "te11st@gmail.com",
           "password": "xxjsedggsjdqw",
           "account": "te1s11t",
           "for_password": "asdsafeaesgfrfd",
       }
       re = requests.post(url, headers = header, json=json)
       print(re.text)
