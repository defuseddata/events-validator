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

## ⚙️ Environment Variables

| Variable | Description |
| :--- | :--- |
| `BUCKET_NAME` | The GCS bucket where schemas are stored. |
| `GCP_PROJECT` | Your Google Cloud Project ID. |
| `REPO_JSON_FILE` | Filename for the parameter repository (default: `repo.json`). |
| `GOOGLE_APPLICATION_CREDENTIALS` | (Local Only) Path to your GCP service account key. |

---

## 📄 License

This component is part of the Events Validator project and is licensed under the **GNU General Public License (GPL)**.
