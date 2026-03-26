# Events Validator (Core)

A scalable, serverless solution for real-time JSON event validation on Google Cloud Platform. It allows anyone to easily validate the quality of any in-app event data (e.g., coming from server-side Google Tag Manager) before it hits your analytics or marketing destinations.

## 🏗️ Architecture

```mermaid
graph TD
    %% Actors
    User((User))
    Source((Event Source))

    %% UI Path
    LB[HTTPS Load Balancer]
    IAP{Identity-Aware Proxy}
    WebUI[Streamlit UI<br/>Cloud Run]

    %% API Path
    APIGW[API Gateway]
    CF[Validator Function<br/>Cloud Functions]

    %% Data
    GCS[(GCS Schema Bucket)]
    BQ[(BigQuery Logs)]

    %% UI Flow
    User -->|HTTPS| LB
    LB --> IAP
    IAP -->|Authorized| WebUI
    WebUI <-->|Read / Write| GCS

    %% API Flow
    Source -->|REST + API Key| APIGW
    APIGW --> CF
    CF -->|Fetch Schema| GCS
    CF -->|Write Logs| BQ
```

## 📁 Project Structure

- **`validator_src/`**: Node.js source code for the Cloud Function.
- **`terraform_backend/`**: Infrastructure as Code (Terraform) for backend services - Cloud Function, BigQuery, GCS buckets, API Gateway.
- **`terraform_ui/`**: Infrastructure as Code (Terraform) for UI services - Streamlit Cloud Run, Load Balancer, IAP authentication.
- **`streamlit_ev/`**: (Optional) UI for schema management and parameter building.

## 🚀 Key Features

*   **Dynamic Schema Loading**: Loads JSON schemas from GCS based on event names.
*   **BigQuery Logging**: Automatically logs validation results and processing errors for auditing.
*   **Performance Optimized**: Parallel fetching and analysis (GCS + Health checks) ensures a snappy UI even with 100+ schemas.
*   **API Gateway Secured**: Protected by API Keys with automated managed service activation.
*   **Fully Automated**: One-click deployment with built-in propagation delays for stability.
*   **GA4 Ready**: Pre-loaded with 36 recommended GA4 event schemas and a master parameter repository.

## 🏷️ Sample GTM Setup

To validate data from Server-Side Google Tag Manager (sGTM), send the entire Event Data object to the validator function, eg. using the **"JSON HTTP Request"** tag (e.g., the popular template by stape.io) following the following steps:

1.  **Tag Type**: Use the **JSON HTTP Request** tag.
2.  **Destination URL**: Set to your `https://<API_GATEWAY_URL>/eventsValidator?key=<API_KEY>`.
3.  **Body**: Select the "Include in the body all Event Data" option.
4.  **Triggering**: It is **highly recommended** to sample incoming data based on volume to manage costs.
    *   *Option*: Use a specific Trigger in GTM to select only certain event types (e.g., `purchase`, `sign_up`) or validation-prone events.

## 📋 Event Schema & Validation

The validator expects a JSON body with a `data` object containing the event details.

### Expected Format
```json
{
  "data": {
    "event_name": "your_event_name",
    "param_1": "value_1",
    "param_2": 123
  }
}
```

### ✅ Validation Capabilities

The validator supports two levels of features: those accessible via the **Streamlit UI** (for easy management) and the full set supported by the **Cloud Function** (for advanced use cases via manual schema editing).

#### 1. Streamlit UI (No-Code)
The UI allows you to define these validations visually:
*   **Structure Validation**: Automatically checks if required parameters are present in the event.
*   **Optional Fields**: Mark fields as Optional (validation is skipped if the field is missing).
*   **Conditional Validation**: Validate a field ONLY if another specific parameter is present (e.g., `item_id` required only if `item_list_name` exists).
*   **Type Checking**: `string`, `number`, `boolean`, `array`.
*   **Exact Match**: Enforce a specific value (e.g., `event_name` must be `purchase`).
*   **Regex Pattern**: Validate strings against a Regular Expression (e.g., `^user_\d+$`).
*   **Array Items**: Define a schema for items within an array.
*   **"Any" Value**: Enforces the **Type** but ignores the specific value.
*   **Nullable Numbers**: In the UI, clearing a number field sets it to "empty" (null/undefined) rather than `0`.

#### 2. Cloud Function (Full Engine)
The core validation engine (`validator_src`) supports additional advanced features if you edit JSON schemas manually:
*   **Object Type**: Validate nested JSON objects (not just arrays of objects).
*   **Exact Length**: Validate that an array or string has a specific exact length (via `length` property in JSON).



#### ℹ️ Supported Data Types
| Type | Description | UI Support | Code Support |
| :--- | :--- | :---: | :---: |
| `string` | Text values. | ✅ | ✅ |
| `number` | Integers or Floats. | ✅ | ✅ |
| `boolean` | `true` or `false`. | ✅ | ✅ |
| `array` | List of items (can have nested schemas). | ✅ | ✅ |
| `object` | Nested JSON object. | ❌ | ✅ |
| **regex** | Regular Expression Pattern. | ❌ | ✅ |

> [!TIP]
> **Regex Best Practice**: For strict validation, always use start (`^`) and end (`$`) anchors. Without them, the validator accepts partial matches (e.g., pattern `\d+` will validly match `"abc123xyz"`).

### 🔧 Advanced Schema Configuration (Manual Edit)

To utilize features not yet available in the UI (like nested Objects, Regex patterns, or exact length checks), you can manually edit the JSON schema file in your Google Cloud Storage bucket.

#### 1. Nested Object Validation
Use this structure to validate a generic object (e.g. `user_info`) containing specific fields.

```json
"user_info": {
  "type": "object",
  "nestedSchema": {
    "user_id": { "type": "string" },
    "is_active": { "type": "boolean" }
  }
}
```

#### 2. Exact Length (`length`)
Validates that a **String** or **Array** has an exact specific length.
*(Note: This is strictly for exact length, not min/max).*

```json
"transaction_id": {
  "type": "string",
  "length": 10
},
"items": {
  "type": "array",
  "length": 3,
  "nestedSchema": { ... }
}
```

#### 3. Optional Fields
By default, the validator treats every field defined in the schema as **Required**. If a required field is missing or empty, validation fails.
Use `"optional": true` to allow a field to be missing, `null`, or an empty string.

```json
"promo_code": {
  "type": "string",
  "optional": true
}
```



## 💰 Cost Estimation

Running this setup on GCP is designed to be cost-effective for validation workloads.

*   **Approximate Cost**: ~$0.50 per day for ~50,000 processed events.
*   *Includes*: Cloud Functions invocations, Cloud Storage class A/B operations, and minimal BigQuery streaming ingestion.
*   *Note*: Costs may vary based on exact payload size and region.

### 📊 Granular Logging Control
Configure these flags in `terraform_backend/terraform.tfvars` to balance visibility with storage costs:

| Flag | Description |
| :--- | :--- |
| `LOG_VALID_FIELDS_FLAG` | Logs every single validated field (even if correct). |
| `LOG_PAYLOAD_WHEN_ERROR_FLAG` | Attaches the full JSON payload when an error is found. |
| `LOG_PAYLOAD_WHEN_VALID_FLAG` | Attaches the full JSON payload for successful events. |

---

## 🛠 Prerequisites

1.  **GCP Project**: An active Google Cloud Project with **[Billing Account linked](https://console.cloud.google.com/billing)**.
    *   *Crucial*: Many APIs (Compute, Cloud Build, API Gateway) will fail to activate or describe without an active billing account, causing the installer to hang or error.
3.  **Tools**:
    *   [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.5.0)
    *   [gcloud CLI](https://cloud.google.com/sdk/docs/install) (authenticated: `gcloud auth application-default login`)
3.  **Local Node.js**: (Optional, for local testing) Node.js 20+.

## 🔑 Authentication Methods

You have two ways to authenticate Terraform:

### Standard Approach (Recommended)
Simply log in with your Google account in the terminal. Terraform will automatically pick up your permissions (ADC). No `.json` keys required!
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```
*(Note: Your personal account must have sufficient permissions, ideally `Editor` + `Project IAM Admin`)*

### Legacy/CI Approach (Service Account Keys)
If you are deploying via an automated CI/CD pipeline or strictly require a Service Account:
1.  Create a Service Account in the IAM Console.
2.  **Assign Roles**:
    *   `Editor` (Fastest for testing) **OR** the following specific roles:
        *   `API Keys Admin` (For Gateway security)
        *   `ApiGateway Admin` (For the entry point)
        *   `Artifact Registry Administrator` (For UI images)
        *   `BigQuery Admin` (For logs)
        *   `Cloud Functions Admin` & `Cloud Run Admin` (For the validator function and UI)
        *   `Compute Admin` (For Load Balancer and Global IPs)
        *   `IAP Policy Admin` & `IAP Settings Admin` (For UI authentication)
        *   `Project IAM Admin` (To grant permissions to worker accounts)
        *   `Service Account Admin` & `Service Account Key Admin` (To manage identities)
        *   `Service Management Administrator` & `Service Usage Admin` (To enable APIs automatically)
        *   `Storage Admin` (For logs and schemas)
    *   `Service Account User` (Always required for Terraform to deploy resources)
3.  Generate a JSON key.
4.  Uncomment `credentials_file` inside your `terraform.tfvars` files and point it to the downloaded JSON key (e.g. `credentials_file = "credentials.json"`). **Never commit the `.json` key to Git.**

---

## 🔄 GitOps & CI/CD (GitHub Actions)

This project implements a secure **GitOps** workflow using **Workload Identity Federation** (Keyless Authentication).

1.  **Terraform Automation**:
    *   Creates a `Workload Identity Pool` & `Provider` for GitHub in GCP.
    *   Creates a dedicated Service Account for the CI/CD pipeline (`github-actions-uploader`).
    *   Populates your GitHub Repository with initial schemas and configure secrets automatically:
        *   `GCP_WORKLOAD_IDENTITY_PROVIDER`
        *   `GCP_SERVICE_ACCOUNT`
        *   `GCS_BUCKET_NAME`

2.  **Workflow**:
    *   Any push to `main` in your schema repository triggers a GitHub Action.
    *   Authentication is handled via OIDC tokens (No long-lived JSON keys stored in secrets!).
    *   Changed JSON schemas are validated and instantly synced to the GCS bucket.

---

## 📂 File Ownership & Environment

To achieve a "Zero-Touch" experience, Terraform manages most configuration files.

| File | Component | Owned By | Description |
| :--- | :--- | :--- | :--- |
| `terraform_backend/credentials.json` | Backend | **User** | Deployer Service Account key (Manual). |
| `terraform_backend/terraform.tfvars` | Backend | **User** | Backend project configuration (Manual). |
| `terraform_ui/credentials.json` | UI | **User** | Deployer Service Account key (Manual). |
| `terraform_ui/terraform.tfvars` | UI | **User** | UI project configuration (Manual). |
| `streamlit_ev/.env` | UI | **Terraform** | App config: Bucket, Project, etc. |

> [!IMPORTANT]
> Files owned by **Terraform** are managed automatically. Do not edit them manually.

---

## 📦 Deployment Using Wizard (Recommended for Mac/Linux)

To make provisioning flawless and "Zero-Touch", we provide a unified Setup Wizard (`install.sh`) that dynamically configures endpoints, creates Git repositories, and runs Terraform for you without requiring JSON key downloads.

### Step 0: Initial Requirements
1.  **Authenticate your terminal users**:
    *   GCP: `gcloud auth application-default login`
    *   GitHub: `gh auth login`

### Step 1: Run the Wizard
Execute the installer from the root directory:
```bash
./install.sh
```

**The script will interactively:**
1. Verify access to your desired GCP Project and compute regions.
2. Bind Application Default Credentials to bypass limits safely (no `.json` required!).
3. Automatically provision or connect an existing GitHub Repository for schemas.
4. Auto-generate all required `.tfvars` securely without pushing them to Git.
5. Deploy the backend and retrieve Gateway URLs.
6. Gather OAuth credentials and fully deploy the UI via Cloud Build + Cloud Run.

---

## 🚀 Manual Deployment (Alternative / Windows)

The infrastructure is split into two independent projects for flexibility:

> [!IMPORTANT]
> Before running `terraform apply`, you **must** create your own `terraform.tfvars` file from the provided example in each project directory. The `.tfvars` files contain sensitive configuration and are not committed to the repository.

### Step 0: GitHub Preparation (Optional, for GitOps)
1.  **Create a Repository**: Create a new, **empty** private repository on GitHub.com. Do not initialize with README/.gitignore.
2.  **Generate a Token**: Create a Personal Access Token (PAT).
    *   **Classic Token (Recommended)**: Select scopes `repo` (full control) and `workflow`.
    *   **Fine-grained Token**: Must have **Read and Write** access to:
        *   `Contents`
        *   `Secrets`
        *   `Workflows`
        *   `Administration` (Required for Branch Protection rules)

### Step 1: Deploy Backend (Required)

   ```bash
   cd terraform_backend

# Create your configuration file from the example
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with:
# 1. Project details (project_id, region, location)
# 2. GitHub Integration (Optional: github_token, schema_repo_owner, schema_repo_name)
#
# IMPORTANT: Update all placeholder values before proceeding

   terraform init
   terraform apply
   ```
*(Note: The deployment includes a 60s delay to allow Google's API Gateway to propagate. Initial GA4 schemas will be pushed to your GitHub repository automatically.)*

**Save the outputs** - you'll need them for the UI deployment:
```bash
terraform output schemas_bucket
terraform output bq_dataset
terraform output bq_table
```

### Step 2: Deploy UI (Optional)

   ```bash
   cd terraform_ui

# Create your configuration file from the example
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with:
# 1. Project details (project_id, region)
# 2. schemas_bucket (from backend outputs)
# 3. IAP credentials (iap_client_id, iap_client_secret)
# 4. GitHub Integration (Optional: github_token, schema_repo_owner, etc.) for UI capabilities
# IMPORTANT: Update all placeholder values

   terraform init
   terraform apply
   ```

---

## 🧪 Verification

1.  **Get Endpoint Details**:
    ```bash
    cd terraform_backend
    terraform output api_gateway_url
    
    # API Key is sensitive/hidden by default. Use -raw to reveal it:
    terraform output -raw api_key
    ```
2.  **Test the Validator**:
    ```bash
    curl -X POST "https://<URL>/eventsValidator?key=<KEY>" \
    -H "Content-Type: application/json" \
    -d '{
      "data": {
        "event_name": "example",
        "example_param": "success"
      }
    }'
    ```
    *Response:* `{"status":"event valid","eventsLogged":1}`

---

## 💡 Schema Management UI (Streamlit)

The `streamlit_ev/` application provides a "Parameter Repository" approach to schema management.

### Keyless Setup
If you deployed using the steps above:
- **Backend** (`terraform_backend`) has:
  1.  Created the schema bucket and pre-loaded 36 GA4 schemas and `repo.json`.
  2.  Created the BigQuery dataset and table for validation logs.
- **UI** (`terraform_ui`) has:
  1.  Created a dedicated `streamlit-worker` Service Account.
  2.  Granted it `Storage Object Admin` permissions on the schema bucket.
  3.  Granted it `BigQuery Data Viewer` and `Job User` permissions for reading logs.
  4.  Generated `streamlit_ev/.env` with your project, bucket, and BigQuery details.

### Local Start
1.  **Authenticate**: `gcloud auth application-default login`
2.  `cd streamlit_ev`
3.  **Install Dependencies**:
    ```bash
    uv sync
    ```
4.  **Run**:
    ```bash
    uv run streamlit run app/app.py
    ```

### Production Deployment (Cloud Run + IAP)

### Production Deployment (Cloud Run + IAP)

#### 1. Manual Prerequisites
Before deploying to the cloud, you **must** configure the following using Google Cloud Console:
1.  **[OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)**: Set to "Internal" and add `iap.googleapis.com` scope.
2.  **[OAuth Client ID](https://console.cloud.google.com/apis/credentials)**: Create a "Web application" ID.
3.  **Update Config**: Add `iap_client_id`, `iap_client_secret`, and the list of `authorized_users` to your **`terraform_ui/terraform.tfvars`** file.

> [!WARNING]
> **Important for Direct IAP (Cloud Run Preview)**:
> This project uses the new Identity-Aware Proxy integration directly on Cloud Run (Preview feature).
> If you encounter `Error 400: redirect_uri_mismatch` after logging in, you **MUST** add the following to your OAuth Client ID's **Authorized redirect URIs**:
> `https://<YOUR-CLOUD-RUN-URL>/_gcp_iap/authenticate`
>
> *(If you switched back to `use_classic_load_balancer = true`, use: `https://iap.googleapis.com/v1/oauth/clientIds/<YOUR_CLIENT_ID>:handleRedirect`)*

> [!TIP]
> **User Identity Format**: In the `authorized_users` list (within `terraform.tfvars`), ensure you use the proper prefix:
> - Individual: `user:name@example.com`
> - Group: `group:marketing@example.com`

#### 2. Build and Deploy
1.  **Build Image**:
    ```bash
    # Ensure you match the region defined in terraform.tfvars (e.g., europe-west1)
    gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/[PROJECT_ID]/event-validator-ui-repo/event-validator-ui:latest ./streamlit_ev
    ```
2.  **Terraform Apply**:
    ```bash
    cd terraform_ui
    terraform apply
    ```

### Features
- **Params Repo**: Centralized database of parameters with strict type validation.
- **Smart Sync & Diff Review**: See exactly what changed (JSON diff) before syncing Repo updates to GCS.
- **Performance Caching**: Session-based memoization for instant tab switching and bulk operations.
- **Overridable Values**: Assign specific values in the Builder while staying synced with Repo metadata.
- **Empty vs Zero Support**: Robust handling of numeric fields—set fields to "empty" (null) instead of forcing 0.0.
- **Explorer**: Direct visibility and health-check analysis for your GCS schema bucket.
- **Auto-Sync**: Propagate changes from the Repo to all GCS schemas with one click.
- **Health Checks**: Automatically detect when GCS schemas are out of sync with your repository.
- **Direct IAP Integration**: Secure access using Google's native Cloud Run authentication (Preview).

---

## 📄 License & Maintainers

*   **License**: This project is licensed under the **GNU General Public License (GPL)**. It is free to use, fork, and modify.
*   **Contributions**: We encourage contributions! Please fork the repository and submit pull requests.
*   **Roadmap**: View the public roadmap at [github.com/orgs/defuseddata/projects/1](https://github.com/orgs/defuseddata/projects/1).
*   **Maintainer**: Maintained by [Defused Data](https://defuseddata.com).
