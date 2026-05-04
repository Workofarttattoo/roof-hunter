# RoofHunter — Azure Kubernetes (AKS)

## What you get

- **Web**: static React app (`nginx`) — `k8s/web-deployment.yaml`
- **API**: FastAPI dashboard (`src/dashboard_api.py`) — `k8s/api-deployment.yaml`
- **Ingress**: `/`, `/api`, `/images`, `/elevenlabs` → correct service — `k8s/ingress.yaml`

The SPA calls `${VITE_API_BASE}/api/...`. For cluster deploy, build the web image with **empty** `VITE_API_BASE` so the browser uses same-host `/api` (Ingress sends `/api` to the API pod).

## One-time AKS + ACR

```bash
RESOURCE_GROUP=my-rg
AKS=my-aks
ACR=myacrname   # creates myacrname.azurecr.io

az group create -n "$RESOURCE_GROUP" -l eastus
az acr create -g "$RESOURCE_GROUP" -n "$ACR" --sku Basic
az aks create -g "$RESOURCE_GROUP" -n "$AKS" \
  --enable-managed-identity \
  --node-count 2 \
  --attach-acr "$(az acr show -g "$RESOURCE_GROUP" -n "$ACR" --query id -o tsv)"
az aks get-credentials -g "$RESOURCE_GROUP" -n "$AKS" --overwrite-existing
```

## Build and push images

From repo root (after `az acr login -n "$ACR"`):

```bash
ACR_LOGIN=$(az acr show -g "$RESOURCE_GROUP" -n "$ACR" --query loginServer -o tsv)

az acr build -g "$RESOURCE_GROUP" -r "$ACR" \
  --image roof-hunter-web:latest \
  --file web_dashboard/Dockerfile web_dashboard

az acr build -g "$RESOURCE_GROUP" -r "$ACR" \
  --image roof-hunter-dashboard-api:latest \
  --file Dockerfile.dashboard-api .
```

Ensure `leads_manifests/authoritative_storms.db` exists before the API build, or seed it in a follow-up Job; otherwise teaser endpoints may error until the DB is present.

## Install an ingress controller

Example: [NGINX Ingress on AKS](https://learn.microsoft.com/azure/aks/ingress-basic). Set `spec.ingressClassName` in `ingress.yaml` to the class you install (for example `nginx`).

## Deploy manifests

1. Replace `YOUR_REGISTRY.azurecr.io` in `web-deployment.yaml` and `api-deployment.yaml` with `$ACR_LOGIN`.
2. Set `CHANGEME.example.com` in `ingress.yaml` to your DNS name (point an A/AAAA or CNAME record at the ingress public IP / hostname).

```bash
# Preview
kubectl kustomize k8s

kubectl apply -k k8s
kubectl -n roof-hunter get pods,svc,ingress
```

## Local UI against local API

```bash
cd web_dashboard
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

(With an empty `VITE_API_BASE`, the UI expects the API on the same origin — correct for production behind Ingress.)

## Canonical lead CSV (before S3 / `aws_lead_sync`)

Exports from tools differ; normalize locally so every upload has the same columns in the same order:

```bash
python3 scripts/prepare_s3_inbound_csv.py -i messy.csv -o leads_canonical.csv
# optional: keep extra columns after the canonical block
python3 scripts/prepare_s3_inbound_csv.py -i messy.csv -o out.csv --extra lead_id source

aws s3 cp leads_canonical.csv s3://$AWS_LEADS_BUCKET/$AWS_LEADS_OBJECT_KEY
```

See `src/lead_csv_schema.py` (`CANONICAL_LEAD_CSV_FIELDS`). `aws_lead_sync.py` coerces each row to this shape at ingest.

## Secrets (optional)

Create `roof-hunter-api-secrets` in namespace `roof-hunter` with keys such as `ELEVENLABS_API_KEY` and uncomment `envFrom` in a copy of `api-deployment.yaml` if you wire webhooks.

## AWS S3 lead ingest

Configure the API pod with:

- `AWS_REGION` (or `AWS_DEFAULT_REGION`)
- `AWS_LEADS_BUCKET` (required to sync)
- `AWS_LEADS_OBJECT_KEY` (optional; default `roof-hunter/leads/latest.csv`)
- IAM/IRSA or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- Optional `SYNC_API_KEY` — if set, send header `X-Roof-Hunter-Sync` on POST `/api/leads/sync-aws`

CSV headers can include: Address, Zip, City, State, Event_Date, Hail_Magnitude, damage_score, phone, homeowner_name, latitude, longitude.

Use **Command center → Sync from S3** in the UI, or `curl -X POST https://<host>/api/leads/sync-aws`.

CLI: `python3 src/aws_lead_sync.py` (repo root, env loaded; use `--dry-run` to validate only).
