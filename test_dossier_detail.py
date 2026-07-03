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

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

url = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/consult/dossierLegislatif"

payload = {
    "id": "JORFDOLE000048451240"
}

response = requests.post(url, headers=headers, json=payload)

print("Status:", response.status_code)
print(response.text[:8000])

try:
    data = response.json()
    with open("dossier_detail.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Saved to dossier_detail.json")
except Exception as e:
    print("JSON parse error:", e)