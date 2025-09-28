import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:4000/update_forward"
    header = {"content-type" : "application/json"}
    json_data = {
        "pad_code": "AC32010811133",
        "account": "test11",
        "for_email": "dsfhdlgfdghl",
        "for_password": "sdgfdsfg",
        "image_base64": "sufgerfusaiddfefsdsfuvegergtfdrfrjt"
    }
    re = requests.post(url, headers = header, json=json_data)
    print(re.json())