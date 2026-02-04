# Event Validator Schema Repository

This repository contains event validation schemas for the Events Validator platform.

## Quick Start
Since this repository is managed via Terraform, all CI/CD workflows and secrets are pre-configured.

### Structure

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

## Authentication (Workload Identity Federation)
This repository is configured to use **Keyless Authentication** (Workload Identity Federation) for security.

> **Note**: If you deployed using Terraform, all necessary secrets and Workload Identity pools have been configured automatically.

Required Secrets (User-Managed or Terraform-Managed):
- `GCS_BUCKET_NAME`: Target GCS bucket.
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: Full path to the WIF Provider.
- `GCP_SERVICE_ACCOUNT`: Service Account email used for impersonation.

**Legacy Authentication (JSON Keys)** is disabled by default for security reasons.

## UI Configuration

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

## Local Development

To test schemas locally:

```bash
# Validate JSON syntax
for f in schemas/*.json; do python3 -c "import json; json.load(open('$f'))"; done
```

## Contributing

1. Create a feature branch: `git checkout -b feature/new-event-schema`
2. Add or modify schemas in the `schemas/` directory
3. Ensure JSON is valid and follows the schema format
4. Create a pull request
5. After review and merge, schemas are automatically synced to GCS
