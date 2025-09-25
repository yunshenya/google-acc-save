import requests


if __name__ == '__main__':
    url = "http://103.115.64.73:3000/update_secondary_mail"
    header = {"content-type" : "application/json"}
    json_data = {
        "account": "bimiwr70321@gmail.com",
        "is_boned_secondary_email": True,
        "pad_code": "ACP250924LR2980N"
    }
    re = requests.post(url, headers = header, json=json_data)
    print(re.json())