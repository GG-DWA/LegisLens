from dotenv import load_dotenv
import os
import requests

load_dotenv()

client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")

url = "https://oauth.piste.gouv.fr/api/oauth/token"

data = {
    "grant_type": "client_credentials",
    "scope": "openid"
}

response = requests.post(
    url,
    data=data,
    auth=(client_id, client_secret)
)

print("Status:", response.status_code)
print(response.text)