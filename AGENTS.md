# AGENTS.md - AI Agent Guide for Events Validator

## Project Overview

**Events Validator** is a serverless JSON event validation platform deployed on Google Cloud Platform. It validates event data quality in real-time before it reaches analytics or marketing destinations, with a focus on Server-Side Google Tag Manager (sGTM) and GA4 events.

### Core Components
- **Validator Function**: Node.js Cloud Function that validates events against JSON schemas
- **Schema Management UI**: Streamlit web application for schema CRUD operations
- **Infrastructure**: Fully automated Terraform deployment on GCP
- **Pre-loaded Assets**: 36 GA4 event schemas and parameter repository

### Architecture Pattern
```
Event Source → API Gateway (API Key) → Cloud Function (Validator) → BigQuery Logs
                                            ↓
                                     GCS Schema Bucket
                                            ↑
                                     Cloud Run (Streamlit UI) ← IAP Auth
```

---

## Directory Structure

```
events-validator/
├── validator_src/              # Node.js Cloud Function (core validator)
│   ├── index.js               # Main HTTP handler (103 lines)
│   └── helpers/
│       ├── validationHelpers.js    # Schema validation logic (164 lines)
│       ├── cloudHelpers.js         # GCS & BigQuery integration (53 lines)
│       └── loggingHelpers.js       # Event logging (59 lines)
│
├── streamlit_ev/              # Python Streamlit UI
│   ├── app/
│   │   ├── app.py            # Navigation & routing (60 lines)
│   │   ├── builder.py        # Visual schema editor (247 lines)
│   │   ├── explorer.py       # Schema browser & health checks (80 lines)
│   │   ├── repo.py           # Parameters repository manager (650 lines)
│   │   ├── export.py         # Schema export/import (191 lines)
│   │   ├── validation_report.py  # BigQuery logs viewer (112 lines)
│   │   ├── home.py           # Dashboard (69 lines)
│   │   └── helpers/
│   │       ├── gcp.py        # GCS/BigQuery clients (144 lines)
│   │       ├── helpers.py    # Schema conversions (453 lines)
│   │       ├── updater.py    # Schema diffing & bulk updates (313 lines)
│   │       └── import_export.py
│   ├── Dockerfile            # Multi-stage container build
│   └── pyproject.toml        # Python dependencies (uv)
│
├── terraform_ev/              # Infrastructure as Code
│   ├── main.tf               # GCP service activation
│   ├── variables.tf          # Configuration variables (100 lines)
│   ├── cloudfunction.tf      # Cloud Functions deployment
│   ├── gateway.tf            # API Gateway configuration
│   ├── storage.tf            # GCS buckets & schema uploads
│   ├── bigquery.tf           # BigQuery dataset & tables
│   ├── streamlit_app.tf      # Cloud Run & Load Balancer
│   ├── streamlit_sa.tf       # Service accounts & IAM
│   ├── outputs.tf            # Terraform outputs
│   └── src/
│       ├── templates/
│       │   └── gateway_config_template.yaml.tpl  # OpenAPI spec
│       ├── bq_schema/
│       │   └── bq_schema.json         # BigQuery table schema
│       ├── GA4 Recommended/
│       │   ├── schemas/               # 36 GA4 event schemas
│       │   └── repo.json              # GA4 parameter repository
│       └── test_schemas/
│           └── example.json
│
└── README.md                  # Main documentation
```

---

## Technology Stack

### Backend (Validator Function)
- **Runtime**: Node.js 20
- **Framework**: @google-cloud/functions-framework
- **Dependencies**:
  - @google-cloud/storage (GCS integration)
  - @google-cloud/bigquery (logging)
  - uuid (event IDs)
  - node-fetch (HTTP utilities)

### Frontend (Schema Management UI)
- **Framework**: Streamlit 1.52+
- **Runtime**: Python 3.12
- **Key Libraries**:
  - streamlit-option-menu (navigation)
  - pandas/polars (data manipulation)
  - altair (visualization)
  - google-cloud-storage, google-cloud-bigquery
  - reportlab (PDF export)
- **Package Manager**: uv (fast pip replacement)

### Infrastructure
- **IaC**: Terraform 1.5+
- **GCP Services**:
  - Cloud Functions (validator compute)
  - Cloud Run (UI container runtime)
  - API Gateway (REST API management)
  - Cloud Storage (schema/code storage)
  - BigQuery (validation logs warehouse)
  - Identity-Aware Proxy (OAuth authentication)
  - Load Balancer (HTTPS frontend)
  - Artifact Registry (container images)

---

## Key Files & Their Responsibilities

### Validator Function (Node.js)

**[validator_src/index.js](validator_src/index.js)** (103 lines)
- Main HTTP handler for Cloud Functions
- Extracts event data from configurable JSON path
- Orchestrates schema loading and validation
- Returns validation results and logs to BigQuery

**[validator_src/helpers/validationHelpers.js](validator_src/helpers/validationHelpers.js)** (164 lines)
- Core validation logic
- Type checking: string, number, boolean, array, object
- Constraint validation: value exactness, contains matching, regex, length
- Nested schema validation for arrays and objects
- Required vs optional field handling

**[validator_src/helpers/cloudHelpers.js](validator_src/helpers/cloudHelpers.js)** (53 lines)
- GCS schema loading (`loadSchemaFromGCS`)
- BigQuery log insertion (`logEventToBigQuery`)
- Error handling for cloud operations

**[validator_src/helpers/loggingHelpers.js](validator_src/helpers/loggingHelpers.js)** (59 lines)
- Formats validation logs with configurable verbosity
- Supports field-level logging, payload logging on error/success
- Creates structured BigQuery-compatible log entries

### Streamlit UI (Python)

**[streamlit_ev/app/app.py](streamlit_ev/app/app.py)** (60 lines)
- Main navigation menu
- Page routing logic
- Session state initialization

**[streamlit_ev/app/builder.py](streamlit_ev/app/builder.py)** (247 lines)
- Visual schema editor interface
- Field creation with type, value, regex constraints
- Support for nested arrays and objects
- Export schema to GCS

**[streamlit_ev/app/explorer.py](streamlit_ev/app/explorer.py)** (80 lines)
- Lists all schemas in GCS bucket
- Health checks: compares schemas with repo.json
- Auto-repair functionality for outdated schemas
- Shows "outdated" badges when parameters differ

**[streamlit_ev/app/repo.py](streamlit_ev/app/repo.py)** (650 lines)
- **Critical file**: Single source of truth for parameters
- Parameter CRUD operations
- Impact analysis: shows which schemas use each parameter
- Bulk update propagation with dry-run diffs
- Transactional schema updates

**[streamlit_ev/app/validation_report.py](streamlit_ev/app/validation_report.py)** (112 lines)
- BigQuery validation logs dashboard
- Error trends visualization
- Filtering by date range, event type, validation status

**[streamlit_ev/app/helpers/gcp.py](streamlit_ev/app/helpers/gcp.py)** (144 lines)
- GCS client wrapper (`get_gcs_client`, `list_bucket_files`, etc.)
- BigQuery client wrapper (`get_bq_client`, `query_bq`)
- Credential management for local and Cloud Run environments

**[streamlit_ev/app/helpers/helpers.py](streamlit_ev/app/helpers/helpers.py)** (453 lines)
- Schema format conversions (UI ↔ JSON)
- Parameter extraction and merging
- UI component helpers (buttons, displays)
- Schema validation utilities

**[streamlit_ev/app/helpers/updater.py](streamlit_ev/app/helpers/updater.py)** (313 lines)
- Schema diffing logic
- Bulk parameter updates
- Preview changes before committing
- Rollback capabilities

### Terraform Infrastructure

**[terraform_ev/variables.tf](terraform_ev/variables.tf)** (100 lines)
- Project configuration variables
- Logging flags: `LOG_VALID_FIELDS_FLAG`, `LOG_PAYLOAD_WHEN_ERROR_FLAG`, etc.
- Event structure: `EVENT_NAME_ATTRIBUTE`, `EVENT_DATA_PATH`
- OAuth credentials for IAP

**[terraform_ev/cloudfunction.tf](terraform_ev/cloudfunction.tf)** (43 lines)
- Cloud Function resource definition
- Environment variable injection
- Function source deployment from GCS

**[terraform_ev/gateway.tf](terraform_ev/gateway.tf)** (95 lines)
- API Gateway configuration
- OpenAPI spec generation from template
- API key creation and management

**[terraform_ev/storage.tf](terraform_ev/storage.tf)** (46 lines)
- GCS bucket creation
- Uploads GA4 schemas and repo.json
- Function source code upload

**[terraform_ev/bigquery.tf](terraform_ev/bigquery.tf)** (16 lines)
- BigQuery dataset creation
- Validation logs table with schema from JSON

**[terraform_ev/streamlit_app.tf](terraform_ev/streamlit_app.tf)** (80+ lines)
- Cloud Run service deployment
- Load Balancer configuration
- Identity-Aware Proxy setup
- SSL certificate management

---

## Data Flow & Interactions

### Event Validation Flow

```
1. Client POST → API Gateway
   Headers: { "key": "<API_KEY>" }
   Body: { "data": { "event_name": "purchase", "amount": 99.99 } }

2. API Gateway validates key → routes to Cloud Function

3. Cloud Function (index.js):
   - Extracts event data from req.body[EVENT_DATA_PATH]
   - Extracts event_name from event[EVENT_NAME_ATTRIBUTE]
   - Constructs schema filename: "${event_name}.json"

4. cloudHelpers.loadSchemaFromGCS():
   - Downloads schema from GCS bucket
   - Parses JSON schema

5. validationHelpers.validateEvent():
   - Checks required vs optional fields
   - Validates types (string, number, boolean, array, object)
   - Checks value constraints (exact, contains, regex)
   - Validates nested schemas recursively
   - Collects validation errors or successes

6. loggingHelpers.createEventLog():
   - Formats log entries based on verbosity flags
   - Includes payload if configured

7. cloudHelpers.logEventToBigQuery():
   - Inserts rows to BigQuery event_data_table

8. Response: { "status": "event valid|invalid", "eventsLogged": 1 }
```

### Schema Management Flow

```
1. User authenticates via IAP → Cloud Run (Streamlit)

2. Navigation (app.py) → Select page:
   - Home: Documentation
   - Explorer: Browse schemas, health checks
   - Builder: Create/edit schemas
   - Params Repo: Manage parameters
   - Export: Download/upload schemas
   - Validation Report: View BigQuery logs

3. Builder Workflow:
   - Define fields with types and constraints
   - Preview JSON schema
   - Save to GCS → gcp.upload_to_gcs()

4. Parameters Repo Workflow:
   - Load repo.json from GCS
   - Edit parameter definitions
   - Run impact analysis (which schemas use this param)
   - Preview diffs for all affected schemas
   - Commit updates → updater.bulk_update_schemas()
   - Save updated schemas to GCS

5. Explorer Workflow:
   - List all schemas from GCS
   - For each schema:
     - Extract parameters → helpers.extract_parameters()
     - Compare with repo.json
     - Show "outdated" if mismatch
   - Click "Update from Repo" → auto-repair
```

### Component Interactions

```
┌─────────────────────────────────────┐
│       GCS Schema Bucket             │
│  (schemas/*.json, repo.json)        │
└──────┬─────────────────┬────────────┘
       │ read            │ read/write
       │                 │
┌──────▼─────────┐  ┌───▼──────────────┐
│ Cloud Function │  │ Cloud Run        │
│ (Validator)    │  │ (Streamlit UI)   │
│                │  │                  │
│ index.js       │  │ builder.py       │
│ validation     │  │ explorer.py      │
│ Helpers        │  │ repo.py          │
└──────┬─────────┘  └───┬──────────────┘
       │ write logs     │ query logs
       └────────┬───────┘
                │
         ┌──────▼──────────┐
         │   BigQuery      │
         │ event_data_table│
         └─────────────────┘
```

---

## Environment Variables

### Cloud Function Variables
Set in [terraform_ev/cloudfunction.tf](terraform_ev/cloudfunction.tf):

- `SCHEMA_BUCKET` - GCS bucket name for schemas
- `BQ_DATASET` - BigQuery dataset ID
- `BQ_TABLE` - BigQuery table ID
- `EVENT_NAME_ATTRIBUTE` - JSON path to event name (default: "event_name")
- `EVENT_DATA_PATH` - JSON path to event data (default: "data")
- `LOG_VALID_FIELDS` - Log each validated field (true/false)
- `LOG_PAYLOAD_WHEN_ERROR` - Attach payload on error (true/false)
- `LOG_PAYLOAD_WHEN_VALID` - Attach payload on success (true/false)

### Streamlit UI Variables
Set in [streamlit_ev/Dockerfile](streamlit_ev/Dockerfile) or Cloud Run config:

- `BUCKET_NAME` - GCS bucket name
- `GCP_PROJECT` - GCP project ID
- `REPO_JSON_FILE` - Repo filename (default: "repo.json")
- `GOOGLE_APPLICATION_CREDENTIALS` - Service account key path (local dev only)

---

## Schema Format & Validation Rules

### Schema Structure

Schemas are JSON objects where each key represents a field name, and the value defines validation rules:

```json
{
  "event_name": {
    "type": "string",
    "value": "purchase",
    "description": "The event name",
    "required": true
  },
  "amount": {
    "type": "number",
    "description": "Purchase amount",
    "optional": true
  },
  "category": {
    "type": "string",
    "value": "*electronics",
    "description": "Product category (contains match)"
  },
  "items": {
    "type": "array",
    "length": 3,
    "description": "Items in cart",
    "nestedSchema": {
      "product_id": { "type": "string", "required": true },
      "quantity": { "type": "number", "regex": "^[1-9][0-9]*$" }
    }
  }
}
```

### Supported Validation Types

Implemented in [validator_src/helpers/validationHelpers.js](validator_src/helpers/validationHelpers.js):

1. **Type Validation**
   - `string` - Non-empty string (or empty if optional)
   - `number` - Integer or float
   - `boolean` - true/false
   - `array` - Array with optional nested schema
   - `object` - Object with optional nested schema

2. **Value Constraints**
   - `value: "exact"` - Exact string match
   - `value: "*contains"` - Prefix with `*` for substring match
   - `regex: "^pattern$"` - Regex pattern matching
   - `length: 5` - Array length validation

3. **Field Properties**
   - `required: true` - Field must be present
   - `optional: true` - Field is optional
   - `description: "text"` - Documentation (not used in validation)
   - `nestedSchema: {...}` - Schema for array items or object properties

### Validation Logic Flow

See [validator_src/helpers/validationHelpers.js:validateEvent](validator_src/helpers/validationHelpers.js):

1. Check all required fields are present
2. For each field in event data:
   - Verify field exists in schema (or log unknown field)
   - Validate type matches schema
   - Validate value constraints (exact, contains, regex)
   - For arrays: validate length and nested schema
   - For objects: recursively validate nested schema
3. Collect errors or success logs
4. Return validation result

---

## Common Development Tasks

### 1. Modify Validation Logic

**File**: [validator_src/helpers/validationHelpers.js](validator_src/helpers/validationHelpers.js)

To add a new validation type:
1. Add new type check in `validateFieldType()` (line ~50)
2. Add constraint logic in `validateFieldValue()` (line ~80)
3. Update schema format documentation

### 2. Add New UI Page

**Files**: [streamlit_ev/app/](streamlit_ev/app/)

1. Create new page file: `streamlit_ev/app/my_page.py`
2. Import and add to navigation in [streamlit_ev/app/app.py](streamlit_ev/app/app.py)
3. Follow existing patterns (use helpers from `helpers/gcp.py`)

### 3. Change Event Structure

**Files**: [terraform_ev/variables.tf](terraform_ev/variables.tf), [terraform_ev/cloudfunction.tf](terraform_ev/cloudfunction.tf)

1. Update `EVENT_DATA_PATH` or `EVENT_NAME_ATTRIBUTE` in `variables.tf`
2. Run `terraform apply` to update Cloud Function env vars
3. Test with new event structure

### 4. Add New GCP Service

**Files**: [terraform_ev/](terraform_ev/)

1. Add service activation in [terraform_ev/main.tf](terraform_ev/main.tf)
2. Create new `.tf` file (e.g., `pubsub.tf`)
3. Update service account permissions in [terraform_ev/streamlit_sa.tf](terraform_ev/streamlit_sa.tf)
4. Add outputs in [terraform_ev/outputs.tf](terraform_ev/outputs.tf)

### 5. Modify BigQuery Schema

**Files**: [terraform_ev/src/bq_schema/bq_schema.json](terraform_ev/src/bq_schema/bq_schema.json), [terraform_ev/bigquery.tf](terraform_ev/bigquery.tf)

1. Edit JSON schema in `bq_schema.json`
2. Update table creation in `bigquery.tf`
3. Modify logging logic in [validator_src/helpers/loggingHelpers.js](validator_src/helpers/loggingHelpers.js)
4. Run `terraform apply` (may require table recreation)

### 6. Update GA4 Schemas

**Files**: [terraform_ev/src/GA4 Recommended/](terraform_ev/src/GA4%20Recommended/)

1. Edit schemas in `GA4 Recommended/schemas/*.json`
2. Update `repo.json` if parameters change
3. Run `terraform apply` to upload to GCS
4. Use Explorer UI to verify health

---

## Deployment & Testing

### Initial Deployment

```bash
cd terraform_ev

# 1. Configure credentials
cp terraform.tfvars.example terraform.tfvars
# Edit with: project_id, region, credentials_file, iap_client_id, etc.

# 2. Initialize Terraform
terraform init

# 3. Deploy all infrastructure
terraform apply

# 4. Get outputs
terraform output api_gateway_url
terraform output api_key
terraform output streamlit_url
```

### Testing Validator Function

```bash
# Test with curl
curl -X POST "$(terraform output -raw api_gateway_url)?key=$(terraform output -raw api_key)" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "event_name": "purchase",
      "amount": 99.99,
      "currency": "USD"
    }
  }'

# Expected response:
# {"status":"event valid","eventsLogged":1}
```

### Local Development

**Validator Function**:
```bash
cd validator_src
npm install
npm start  # Runs functions-framework locally
```

**Streamlit UI**:
```bash
cd streamlit_ev

# Install dependencies with uv
uv sync

# Set environment variables
export BUCKET_NAME="your-bucket"
export GCP_PROJECT="your-project"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"

# Run locally
streamlit run app/app.py
```

### Updating Infrastructure

```bash
cd terraform_ev

# Preview changes
terraform plan

# Apply changes
terraform apply

# Destroy (careful!)
terraform destroy
```

---

## Security Considerations

### Authentication & Authorization

1. **API Gateway**: Protected with API keys
   - Keys generated in [terraform_ev/gateway.tf](terraform_ev/gateway.tf)
   - Passed as query parameter: `?key=<API_KEY>`
   - Regenerate keys by running `terraform apply`

2. **Streamlit UI**: Protected with Identity-Aware Proxy (IAP)
   - OAuth 2.0 authentication
   - Configure in [terraform_ev/streamlit_app.tf](terraform_ev/streamlit_app.tf)
   - Authorized users list in `terraform.tfvars`

3. **Service Accounts**: Minimal IAM permissions
   - Cloud Function SA: read GCS, write BigQuery
   - Cloud Run SA: read/write GCS, read BigQuery
   - Defined in [terraform_ev/streamlit_sa.tf](terraform_ev/streamlit_sa.tf)

### Best Practices

- Never commit `credentials.json` to git (already in `.gitignore`)
- Rotate API keys regularly
- Use deletion protection for critical resources
- Review IAM permissions periodically
- Enable VPC Service Controls for production
- Use Secret Manager for sensitive config (future enhancement)

---

## Cost Optimization

**Current Estimate**: ~$0.50/day for 50,000 events/day

### Cost Breakdown

- **Cloud Functions**: $0.0000002667 per invocation + compute time
- **Cloud Run**: $0.00002400 per vCPU-second (with generous free tier)
- **Cloud Storage**: Minimal (Class A/B operations)
- **BigQuery**: Streaming inserts ($0.01 per 200 MB)
- **API Gateway**: $3 per million calls
- **Load Balancer**: ~$18/month base + data processing

### Optimization Tips

1. Reduce BigQuery logging verbosity:
   - Set `LOG_VALID_FIELDS_FLAG = false`
   - Set `LOG_PAYLOAD_WHEN_VALID_FLAG = false`

2. Use Cloud Functions min instances = 0 (cold starts acceptable)

3. Configure BigQuery partitioning/clustering for large datasets

4. Use GCS lifecycle policies to archive old schemas

---

## Troubleshooting

### Common Issues

**Issue**: Cloud Function returns 500 error
- Check logs: `gcloud functions logs read validateEvent`
- Verify schema exists in GCS bucket
- Check BigQuery permissions

**Issue**: Schema validation failing unexpectedly
- Review schema JSON syntax
- Check field types match event data
- Enable `LOG_VALID_FIELDS` for debugging

**Issue**: Streamlit UI not loading schemas
- Verify `BUCKET_NAME` env var is correct
- Check Cloud Run service account has GCS read permissions
- View Cloud Run logs: `gcloud run logs read event-validator-ui`

**Issue**: IAP authentication not working
- Verify OAuth client ID/secret in `terraform.tfvars`
- Check authorized users list
- Ensure user has `IAP-secured Web App User` role

### Useful Commands

```bash
# View Cloud Function logs
gcloud functions logs read validateEvent --region us-central1

# View Cloud Run logs
gcloud run logs read event-validator-ui --region us-central1

# List schemas in GCS
gsutil ls gs://your-bucket/

# Query BigQuery validation logs
bq query --use_legacy_sql=false \
  'SELECT * FROM `project.dataset.event_data_table` LIMIT 10'

# Test local function
cd validator_src && npm start
curl -X POST http://localhost:8080 -d '{"data":{"event_name":"test"}}'
```

---

## Git Workflow

### Current Branch
- **Main**: `main`
- **Current**: `feat_streamlit-updates`

### Recent Changes
- Added `uv` package manager to Streamlit
- Implemented granular payload logging with feature flags
- Deployed production-ready Streamlit with IAP
- Pre-loaded 36 GA4 schemas and repo.json

### Modified Files (Staged)
```
M  .gitignore
M  streamlit_ev/app/app.py
M  streamlit_ev/app/helpers/gcp.py
M  streamlit_ev/app/repo.py
M  streamlit_ev/pyproject.toml
M  streamlit_ev/uv.lock
D  streamlit_ev/hello.py
D  streamlit_ev/requirements.txt
A  streamlit_ev/app/validation_report.py
A  streamlit_ev/repo.json
A  terraform_ev/credentials.json  # Should be removed before commit!
```

**Warning**: [terraform_ev/credentials.json](terraform_ev/credentials.json) should NOT be committed (contains service account keys)

---

## Key Insights for AI Agents

### Design Patterns

1. **Separation of Concerns**
   - Validator: Stateless, pure validation logic
   - UI: State management with Streamlit session state
   - Infrastructure: Declarative Terraform modules

2. **Single Source of Truth**
   - Parameters defined once in `repo.json`
   - Schemas reference parameters, not duplicate them
   - Health checks ensure consistency

3. **Configurability**
   - Validation behavior controlled via env vars
   - Event structure customizable via JSON paths
   - Logging verbosity adjustable per environment

4. **Serverless-First**
   - No server management
   - Auto-scaling built-in
   - Pay-per-use pricing

### Extension Points

1. **New Validation Types**: Add to `validationHelpers.js`
2. **New UI Features**: Add pages to `streamlit_ev/app/`
3. **Additional Cloud Services**: Add `.tf` files
4. **Custom Event Formats**: Configure `EVENT_DATA_PATH`
5. **Integration Points**: Use BigQuery logs for downstream analytics

### Code Quality Notes

- **Validator**: Well-modularized, clear separation of concerns
- **Streamlit**: Some files are long (repo.py at 650 lines) - consider splitting
- **Terraform**: Clean module structure, good use of variables
- **Documentation**: Comprehensive README, but could benefit from API docs

### Performance Considerations

- Schema caching not implemented (each request loads from GCS)
- BigQuery streaming can be expensive at high volume
- Cold starts on Cloud Functions (~1-2 seconds)
- Streamlit UI can be slow on large schema sets

### Future Enhancement Ideas

1. In-memory schema caching with TTL
2. Webhook notifications for validation failures
3. Schema versioning and rollback
4. A/B testing for schema changes
5. Integration with Pub/Sub for async validation
6. GraphQL API for schema management
7. Automated schema generation from sample events
8. Machine learning for anomaly detection

---

## Quick Reference

### File Locations
- **Validator Entry Point**: [validator_src/index.js:16](validator_src/index.js#L16)
- **Core Validation Logic**: [validator_src/helpers/validationHelpers.js:50](validator_src/helpers/validationHelpers.js#L50)
- **Schema Upload**: [streamlit_ev/app/builder.py:200](streamlit_ev/app/builder.py#L200)
- **Parameter Repository**: [streamlit_ev/app/repo.py](streamlit_ev/app/repo.py)
- **Terraform Variables**: [terraform_ev/variables.tf](terraform_ev/variables.tf)
- **GA4 Schemas**: [terraform_ev/src/GA4 Recommended/schemas/](terraform_ev/src/GA4%20Recommended/schemas/)

### Key Functions
- `validateEvent()` - [validator_src/helpers/validationHelpers.js:30](validator_src/helpers/validationHelpers.js#L30)
- `loadSchemaFromGCS()` - [validator_src/helpers/cloudHelpers.js:10](validator_src/helpers/cloudHelpers.js#L10)
- `logEventToBigQuery()` - [validator_src/helpers/cloudHelpers.js:35](validator_src/helpers/cloudHelpers.js#L35)
- `extract_parameters()` - [streamlit_ev/app/helpers/helpers.py:150](streamlit_ev/app/helpers/helpers.py#L150)
- `bulk_update_schemas()` - [streamlit_ev/app/helpers/updater.py:100](streamlit_ev/app/helpers/updater.py#L100)

### URLs (after deployment)
- API Gateway: `https://<gateway-id>.execute-api.<region>.amazonaws.com/v1/eventsValidator`
- Streamlit UI: `https://<cloud-run-url>.run.app`
- BigQuery Dataset: `project:dataset.event_data_table`

---

**Last Updated**: 2026-01-11
**Project Status**: Production-ready, actively developed
**Primary Maintainer**: Review git log for contributors
