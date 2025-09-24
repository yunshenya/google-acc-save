import requests


if __name__ == '__main__':
       url = "http://103.115.64.73:3000/create_accounts"
       header = {"content-type" : "application/json"}
       json = {
           "for_email": "te11st@gmail.com",
           "password": "xxjsedggsjdqw",
           "account": "te1s11t",
           "for_password": "asdsafeaesgfrfd",
       }
       re = requests.post(url, headers = header, json=json)
       print(re.text)
