# Event Schema Manager (UI)

A specialized Streamlit application for managing, building, and auditing event validation schemas on Google Cloud Storage. This UI acts as the management layer for the **Events Validator** core.

## ✨ Key Features

### 📚 Parameters Repository
*   **Single Source of Truth**: Define parameters (keys, types, descriptions) once and reuse them across multiple event schemas.
*   **Transactional Updates**: Editing a parameter in the repository allows you to propagate changes to all associated schemas in GCP Storage automatically.
*   **Impact Analysis**: View a side-by-side diff of how changes will affect deployed schemas before committing.

### 🔍 Schema Explorer
*   **Cloud Storage Browser**: Directly view and manage JSON schemas stored in your GCP bucket.
*   **Health Checks**: Automatically detects when deployed schemas fall out of sync with the Parameter Repository.
*   **One-Click Repair**: Instantly update outdated schemas to match the latest repository definitions.

### 🔧 Schema Builder
*   **Visual Editor**: Design complex JSON schemas without writing code.
*   **Type Safety**: Built-in support for Strings, Numbers, Booleans, Arrays, and Objects.
*   **Nested Structures**: Create complex array schemas with nested object definitions easily.

---

## 🚀 Local Development

### Prerequisites
*   [uv](https://github.com/astral-sh/uv) (Astral's fast Python package manager)
*   Google Cloud SDK (authenticated)

### Setup
1.  **Authenticate**:
    ```bash
    gcloud auth application-default login
    ```
2.  **Environment Configuration**:
    Copy `.env.example` to `.env` and fill in your GCP details:
    ```bash
    cp .env.example .env
    ```
3.  **Install Dependencies**:
    ```bash
    uv sync
    ```
4.  **Run Application**:
    ```bash
    uv run streamlit run app/app.py
    ```

---

## 🐳 Docker Usage

The application is containerized and optimized for **Cloud Run**.

### Build
```bash
docker build -t event-validator-ui .
```

### Run Locally
```bash
docker run -p 8080:8080 \
  -v $HOME/.config/gcloud:/root/.config/gcloud \
  -e BUCKET_NAME="your-bucket" \
  -e GCP_PROJECT="your-project" \
  event-validator-ui
```

---

## ☁️ Deployment Modes (IAP)

The Terraform configuration supports two deployment modes for securing the application with Identity-Aware Proxy (IAP):

### 1. Direct IAP Integration (Recommended / Default)
*   **Cost**: Low/Free (No dedicated Load Balancer).
*   **Architecture**: Uses Cloud Run's native IAP integration (Preview).
*   **Pros**: Significant cost savings (~$18/mo saved), simpler infrastructure.
*   **Cons**: Experimental feature (Preview)
*   **Configuration**: `use_classic_load_balancer = false` in `terraform.tfvars`.

### 2. Classic Load Balancer
*   **Cost**: ~$18/month + traffic.
*   **Architecture**: Full HTTPS Global Load Balancer + Serverless NEG.
*   **Pros**: Production-grade GA feature, full visibility in Cloud Console, supports custom domains easily.
*   **Cons**: Expensive for small internal tools.
*   **Configuration**: `use_classic_load_balancer = true` in `terraform.tfvars`.


## ⚙️ Environment Variables

| Variable | Description |
| :--- | :--- |
| `BUCKET_NAME` | The GCS bucket where schemas are stored. |
| `GCP_PROJECT` | Your Google Cloud Project ID. |
| `REPO_JSON_FILE` | Filename for the parameter repository (default: `repo.json`). |
| `GOOGLE_APPLICATION_CREDENTIALS` | (Local Only) Path to your GCP service account key. |
| `SCHEMA_REPO_OWNER` | (Optional) GitHub user or organization that owns the schema repository. |
| `SCHEMA_REPO_NAME` | (Optional) Name of the schema repository. **Setting both `SCHEMA_REPO_OWNER` and `SCHEMA_REPO_NAME` switches the app to GitHub mode**; if either is empty it reads and writes GCS directly. |
| `GITHUB_TOKEN` | (Optional) Personal access token with `repo` and `workflow` scopes. Required for saving in GitHub mode. |
| `SCHEMA_REPO_PATH` | (Optional) Folder with schemas inside the repository (default: `schemas`). |
| `SCHEMA_REPO_DEFAULT_BRANCH` | (Optional) Default branch (default: `main`). |

> If you deployed with `terraform_ui`, these variables are written to `.env` for you, taken from the GitHub settings in `terraform_ui/terraform.tfvars`. Terraform regenerates the file on every `apply`, so change them in `terraform.tfvars`, not in `.env`.

---

## 📄 License

This component is part of the Events Validator project and is licensed under the **GNU General Public License (GPL)**.
