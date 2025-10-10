import requests

if __name__ == "__main__":
    url = "http://203.91.72.67:3000/vmos-slide"
    header = {"content-type": "application/json"}
    json_data = {"pade_code":"ACP250423393XF0K","x1":383,"y1":2040,"next_position_wait_time1":1000,"x2":344,"y2":265,"next_position_wait_time2":300,"x3":344,"y3":265,"width":1081,"height":2340}

    re = requests.post(url, headers=header, json=json_data)
    print(re.json())
