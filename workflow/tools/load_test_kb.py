"""Creates a Pinecone serverless index (if missing), embeds a small test knowledge base with OpenAI,
and upserts it. Keys are read from environment variables only (never hard-code them).

  PowerShell:
    $env:OPENAI_API_KEY = "sk-..."
    $env:PINECONE_API_KEY = "pcsk_..."
    python workflow/tools/load_test_kb.py

Prints the values to paste into n8n node "00 - Config" (pineconeIndexHost, pineconeNamespace).
Requires: pip install requests
"""
import os
import sys
import time

import requests

INDEX = os.environ.get("PINECONE_INDEX", "support-kb-test")
NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "test")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")  # 1536 dims
DIM = 1536
API_VERSION = "2024-07"

oai = os.environ.get("OPENAI_API_KEY")
pc = os.environ.get("PINECONE_API_KEY")
if not oai or not pc:
    sys.exit("Set OPENAI_API_KEY and PINECONE_API_KEY environment variables first.")

KB = [
    ("kb-reset-password", "Reset your password",
     "To reset your workspace password, open Settings > Security and click Reset password. You will receive an email with a reset link that is valid for 24 hours. If you do not receive it, check your spam folder and confirm the email address on your account."),
    ("kb-invite-users", "Invite team members",
     "Workspace admins can invite team members from Settings > Members > Invite. Enter the email address and choose a role (Admin, Member or Viewer). The invitation link expires after 7 days and can be resent from the same page."),
    ("kb-export-data", "Export your data",
     "You can export your workspace data as CSV from Settings > Data > Export. Large exports are prepared in the background and a download link is emailed to you when ready. Only workspace admins can run exports."),
    ("kb-billing-invoices", "Find your invoices",
     "Invoices are available to admins under Settings > Billing > Invoices. Each invoice can be downloaded as a PDF. To change the billing email address, use Settings > Billing > Billing contact."),
    ("kb-2fa", "Set up two-factor authentication",
     "To enable two-factor authentication, go to Settings > Security > Two-factor authentication and scan the QR code with an authenticator app. Save the backup codes shown after setup in a safe place."),
    ("kb-support-hours", "Support hours",
     "Our support team answers emails Monday to Friday, 9:00 to 18:00 UTC. Messages received outside these hours are answered on the next business day."),
]

H_PC = {"Api-Key": pc, "X-Pinecone-Api-Version": API_VERSION, "Content-Type": "application/json"}

# 1. Ensure index exists
r = requests.get("https://api.pinecone.io/indexes", headers=H_PC, timeout=30)
r.raise_for_status()
names = [i["name"] for i in r.json().get("indexes", [])]
if INDEX not in names:
    r = requests.post("https://api.pinecone.io/indexes", headers=H_PC, timeout=30, json={
        "name": INDEX, "dimension": DIM, "metric": "cosine",
        "spec": {"serverless": {"cloud": "aws", "region": "us-east-1"}},
    })
    r.raise_for_status()
    print("Created index", INDEX)
for _ in range(60):
    d = requests.get("https://api.pinecone.io/indexes/" + INDEX, headers=H_PC, timeout=30).json()
    if d.get("status", {}).get("ready"):
        break
    time.sleep(3)
host = d["host"]

# 2. Embed
r = requests.post("https://api.openai.com/v1/embeddings", timeout=60,
                  headers={"Authorization": "Bearer " + oai},
                  json={"model": EMBED_MODEL, "input": [t + ". " + x for _, t, x in KB]})
if not r.ok:
    sys.exit("OpenAI error %s: %s" % (r.status_code, r.text[:500]))
vecs =[e["embedding"] for e in r.json()["data"]]

# 3. Upsert (chunk text lives in metadata.text, matching 00 - Config metadataTextField)
r = requests.post("https://" + host + "/vectors/upsert", headers=H_PC, timeout=60, json={
    "namespace": NAMESPACE,
    "vectors": [{"id": i, "values": v, "metadata": {"text": x, "title": t, "url": "https://help.example.com/" + i}}
                for (i, t, x), v in zip(KB, vecs)],
})
r.raise_for_status()
print("Upserted", len(KB), "articles:", r.json())
print("\nPaste into n8n '00 - Config':")
print("  pineconeIndexHost =", "https://" + host)
print("  pineconeNamespace =", NAMESPACE)
print("  metadataTextField = text   (default)")
print("  embeddingModel    =", EMBED_MODEL)
