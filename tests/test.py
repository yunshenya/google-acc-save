import requests


if __name__ == '__main__':
    url = "http://localhost:4000/account/unique"
    header = {"content-type" : "application/json"}
    re = requests.get(url, headers = header)
    print(re.text)
