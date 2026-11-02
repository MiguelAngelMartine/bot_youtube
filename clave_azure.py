"""Guarda en .env la clave del recurso de voz de Azure (hoyformativo-voz) sin tener que copiarla a mano.
Uso (lo ejecuta el usuario en el servidor): .venv/bin/python clave_azure.py
Muestra un código corto; se escribe en https://microsoft.com/devicelogin desde cualquier PC con la cuenta de Azure,
y el script recoge la clave y la región, las guarda en .env y prueba que funcionan. Nunca muestra la clave."""
import sys
from pathlib import Path

import msal
import requests

ENV = Path(__file__).parent / ".env"
RECURSO = "hoyformativo-voz"
M = "https://management.azure.com"

app = msal.PublicClientApplication("04b07795-8ddb-461a-bbee-02f9e1bfe7b2",
                                   authority="https://login.microsoftonline.com/organizations")
flujo = app.initiate_device_flow(scopes=[f"{M}/.default"])
print(f"\n  1. En el PC donde tienes Azure abre: {flujo['verification_uri']}")
print(f"  2. Escribe este código: {flujo['user_code']}")
print("  3. Entra con tu cuenta de Azure y acepta. Aquí se completa solo.\n", flush=True)
tok = app.acquire_token_by_device_flow(flujo)
if "access_token" not in tok:
    sys.exit("No se pudo iniciar sesión: " + tok.get("error_description", "")[:200])
H = {"Authorization": "Bearer " + tok["access_token"]}
for s in requests.get(f"{M}/subscriptions?api-version=2022-12-01", headers=H, timeout=30).json().get("value", []):
    url = f"{M}/subscriptions/{s['subscriptionId']}/providers/Microsoft.CognitiveServices/accounts?api-version=2023-05-01"
    for c in requests.get(url, headers=H, timeout=30).json().get("value", []):
        if c["name"] != RECURSO:
            continue
        clave = requests.post(f"{M}{c['id']}/listKeys?api-version=2023-05-01", headers=H, timeout=30).json()["key1"]
        lineas = [l for l in ENV.read_text(encoding="utf-8").splitlines()
                  if not l.startswith(("AZURE_SPEECH_KEY=", "AZURE_SPEECH_REGION="))]
        lineas += [f"AZURE_SPEECH_KEY={clave}", f"AZURE_SPEECH_REGION={c['location']}"]
        ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        r = requests.post(f"https://{c['location']}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
                          headers={"Ocp-Apim-Subscription-Key": clave, "Content-Length": "0"}, timeout=20)
        print(f"Clave guardada en .env (región {c['location']}, plan {c.get('sku', {}).get('name')}). "
              + ("Prueba: FUNCIONA ✅" if r.ok else f"Prueba: falla ({r.status_code})"))
        sys.exit(0)
sys.exit(f"No encontré el recurso {RECURSO} en tu cuenta de Azure.")
