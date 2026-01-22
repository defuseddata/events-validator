# Event Validator Schema Repository

This repository contains event validation schemas for the Events Validator platform.

## Structure

```
schemas/
  ├── repo.json          # Parameter repository (master definitions)
  ├── purchase.json      # Schema for purchase events
  ├── add_to_cart.json   # Schema for add_to_cart events
  └── ...                # Other event schemas
```

## How It Works

1. **Schemas are the source of truth**: All event schemas live in this repository
2. **GitHub Actions sync to GCS**: When schemas are pushed to `main`, they're automatically synced to Google Cloud Storage
3. **UI reads from this repo**: The Events Validator UI reads schemas directly from this repository
4. **Validator function reads from GCS**: The Cloud Function validator reads from GCS for low-latency validation

## Branch Strategy

| Branch | Purpose | GCS Prefix |
|--------|---------|------------|
| `main` | Production schemas | Root (no prefix) |
| `staging` | Pre-production testing | `staging/` |
| `feature/*` | Development branches | `branches/{branch-name}/` |

## Setup

### 1. Configure GitHub Secrets

Add the following secrets to your repository:

| Secret | Description |
|--------|-------------|
| `GCS_BUCKET_NAME` | Your GCS bucket name (e.g., `event_validator_schemas_bucket-abc123`) |
| `GCP_SA_KEY` | Service account JSON key (for simple auth) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity provider (for keyless auth) |
| `GCP_SERVICE_ACCOUNT` | Service account email (for keyless auth) |

### 2. Choose Authentication Method

**Option A: Service Account Key (simpler)**
- Create a service account with `Storage Object Admin` role
- Download the JSON key
- Add it as `GCP_SA_KEY` secret
- Use the `sync-to-gcs-simple.yml` workflow

**Option B: Workload Identity Federation (more secure)**
- Set up Workload Identity Federation in GCP
- Configure the identity pool to trust GitHub Actions
- Add provider and service account as secrets
- Use the `sync-to-gcs.yml` workflow

### 3. Configure Events Validator UI

In the Events Validator UI environment:

```bash
GITHUB_TOKEN=ghp_xxxxx              # Personal access token or GitHub App token
SCHEMA_REPO_OWNER=your-org          # GitHub org or username
SCHEMA_REPO_NAME=event-schemas      # This repository name
SCHEMA_REPO_PATH=schemas            # Path to schemas folder
SCHEMA_REPO_DEFAULT_BRANCH=main     # Default branch
```

## Schema Format

Each schema file defines the expected structure for an event:

```json
{
  "event_name": {
    "type": "string",
    "value": "purchase"
  },
  "version": {
    "type": "number",
    "value": 1
  },
  "currency": {
    "type": "string",
    "description": "Currency code in ISO 4217 format"
  },
  "value": {
    "type": "number",
    "description": "Total transaction value"
  },
  "items": {
    "type": "array",
    "description": "Product items",
    "nestedSchema": {
      "item_id": {"type": "string"},
      "item_name": {"type": "string"},
      "price": {"type": "number"},
      "quantity": {"type": "number"}
    }
  }
}
```

### Field Types

| Type | Description |
|------|-------------|
| `string` | Text values |
| `number` | Numeric values (integers or decimals) |
| `boolean` | True/false values |
| `array` | Lists with `nestedSchema` for item structure |

### Field Properties

| Property | Required | Description |
|----------|----------|-------------|
| `type` | Yes | The data type |
| `value` | No | Fixed expected value |
| `regex` | No | Pattern for validation (alternative to value) |
| `description` | No | Documentation |
| `nestedSchema` | For arrays | Schema for array items |

## Parameter Repository (repo.json)

The `repo.json` file is a centralized parameter repository that:
- Defines reusable parameters with their types, descriptions, and categories
- Tracks which schemas use each parameter
- Enables bulk updates across all schemas using a parameter

Example:
```json
{
  "currency": {
    "type": "string",
    "description": "Currency in ISO 4217 format",
    "category": "GA4 Recommended",
    "usedInSchemas": ["purchase", "add_to_cart", "checkout"]
  }
}
```

## Workflows

### Main Sync Workflow (`sync-to-gcs.yml`)

- Triggers on push to `main`, `staging`, or `feature/*` branches
- Validates JSON syntax
- Detects changed files (incremental sync)
- Syncs only changed files to GCS
- Supports branch-based prefixes

### Simple Sync Workflow (`sync-to-gcs-simple.yml`)

- Triggers on push to `main` only
- Uses service account key authentication
- Syncs changed files to GCS root (no prefixes)

## Local Development

To test schemas locally:

```bash
# Validate JSON syntax
for f in schemas/*.json; do python3 -c "import json; json.load(open('$f'))"; done

# Sync manually with gsutil
gsutil cp schemas/*.json gs://YOUR_BUCKET/
```

## Contributing

1. Create a feature branch: `git checkout -b feature/new-event-schema`
2. Add or modify schemas in the `schemas/` directory
3. Ensure JSON is valid and follows the schema format
4. Create a pull request
5. After review and merge, schemas are automatically synced to GCS

## Troubleshooting

### Sync Not Working

1. Check GitHub Actions logs for errors
2. Verify secrets are configured correctly
3. Ensure service account has `Storage Object Admin` permission

### Schema Validation Failing

1. Check JSON syntax with a JSON validator
2. Ensure required fields (`event_name`, `version`) are present
3. Verify field types match expectations

### UI Not Showing Updates

1. Check the branch selector matches your working branch
2. Use the "Refresh from GitHub" button
3. Verify `GITHUB_TOKEN` has read access to the repository
