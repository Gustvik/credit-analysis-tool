import base64, requests, json

cid = None
cs = None

with open(r"C:\credit_tool\.env", "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("ROARING_CLIENT_ID="):
            cid = line.split("=", 1)[1]
        elif line.startswith("ROARING_CLIENT_SECRET="):
            cs = line.split("=", 1)[1]

creds = f"{cid}:{cs}"
encoded = base64.b64encode(creds.encode()).decode()

response = requests.post(
    "https://api.roaring.io/token",
    headers={"Authorization": f"Basic {encoded}"},
    data={"grant_type": "client_credentials"}
)

token = response.json().get("access_token")
print("Token hentet:", token[:10], "...")

response2 = requests.get(
    "https://api.roaring.io/no/company/financial-information/1.0/989781707",
    headers={"Authorization": f"Bearer {token}"},
    params={"years": 5}
)

print("Financial status:", response2.status_code)
print(json.dumps(response2.json(), indent=2))
