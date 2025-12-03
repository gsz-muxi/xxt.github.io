# 最简单的调用
import requests

response = requests.post(
    "http://gsz-muxi/xxt:5000/api/run",
    # "http://127.0.0.1:5000/api/run",
    json={
        "username": "19837765338",
        "password": "Cyt2006820.", 
        "list_id": 257040405
        # "username": "16712834527",
        # "password": "ge20040205", 
        # "list_id": 255325225
    }
)

print(response.json())