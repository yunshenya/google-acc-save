import requests

try:
    # url = "http://103.118.254.151/accounts/"
    url = "http://localhost:5000/accounts"
    headers = {"Content-Type": "application/json"}
    data = {"account": "user1", "password": "xyz789"}

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()

    print("Status Code:", response.status_code)
    print("Response:", response.json())

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the server. Is it running at http://localhost:8000/?")
except requests.exceptions.JSONDecodeError:
    print("Error: Response is not valid JSON.")
except requests.exceptions.RequestException as err:
    print(f"An error occurred: {err}")