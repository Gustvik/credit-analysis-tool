import requests
import base64
import os

def _get_credentials():
    try:
        import streamlit as st
        cid = st.secrets["ROARING_CLIENT_ID"]
        cs = st.secrets["ROARING_CLIENT_SECRET"]
        if cid and cs:
            return cid, cs
    except Exception:
        pass

    cid = os.getenv("ROARING_CLIENT_ID")
    cs = os.getenv("ROARING_CLIENT_SECRET")
    if cid and cs:
        return cid, cs

    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_path = os.path.abspath(env_path)
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ROARING_CLIENT_ID="):
                    cid = line.split("=", 1)[1]
                elif line.startswith("ROARING_CLIENT_SECRET="):
                    cs = line.split("=", 1)[1]
    return cid, cs

def get_access_token():
    cid, cs = _get_credentials()
    encoded = base64.b64encode(f"{cid}:{cs}".encode()).decode()
    response = requests.post(
        "https://api.roaring.io/token",
        headers={"Authorization": f"Basic {encoded}"},
        data={"grant_type": "client_credentials"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    raise Exception(f"Token-feil: {response.status_code} {response.text}")

def get_financial_data(org_nr: str, years: int = 5):
    token = get_access_token()
    response = requests.get(
        f"https://api.roaring.io/no/company/financial-information/1.0/{org_nr}",
        headers={"Authorization": f"Bearer {token}"},
        params={"years": years}
    )
    if response.status_code == 200:
        return response.json()
    return {"error": response.status_code, "message": response.text}

def get_company_info(org_nr: str):
    response = requests.get(
        f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_nr}"
    )
    if response.status_code == 200:
        return response.json()
    return {"error": response.status_code}
