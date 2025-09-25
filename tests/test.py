import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:4000/update_forward"
    header = {"content-type" : "application/json"}
    json_data = {
        "account": "test",
        "for_email": "awfrdwf",
        "for_password": "dfgdf"
    }
    re = requests.post(url, headers = header, json=json_data)
    print(re.json())