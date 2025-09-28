import requests


if __name__ == '__main__':
    url = "http://127.0.0.1:4000/account/unique"
    header = {"content-type" : "application/json"}
    # json_data = {
    #     "pad_code": "AC32010811133",
    #     "account": "dskferf",
    #     "password": "dsfhdlgfdghl",
    # }
    re = requests.get(url, headers = header)
    print(re.json())