from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")

token_response = requests.post(
    "https://oauth.piste.gouv.fr/api/oauth/token",
    data={"grant_type": "client_credentials", "scope": "openid"},
    auth=(client_id, client_secret)
)

access_token = token_response.json()["access_token"]

url = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/list/loda"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

payload = {
    "pageNumber": 1,
    "pageSize": 5
}

response = requests.post(url, headers=headers, json=payload)

print("Status:", response.status_code)
print(response.text)

try:
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception:
    pass