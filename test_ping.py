from dotenv import load_dotenv
import os
import requests

load_dotenv()

client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")

token_url = "https://oauth.piste.gouv.fr/api/oauth/token"

token_response = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "scope": "openid"
    },
    auth=(client_id, client_secret)
)

print("Token status:", token_response.status_code)

if token_response.status_code != 200:
    print("Token error:")
    print(token_response.text)
    exit()

access_token = token_response.json()["access_token"]

api_url = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/consult/ping"

headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(api_url, headers=headers)

print("API status:", response.status_code)
print("Headers:")
print(response.headers)
print("Body:")
print(response.text)