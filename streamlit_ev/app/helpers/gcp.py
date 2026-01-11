from google.cloud import storage, bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import json
import os
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
load_dotenv()

bucket_name = os.getenv("BUCKET_NAME")
project = os.getenv("GCP_PROJECT")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
repo_file_name = os.getenv("REPO_JSON_FILE") or "repo.json"

_bucket_ref = None
_bq_client = None


def get_bucket():
    global _bucket_ref
    if _bucket_ref:
        return _bucket_ref
        
    try:
        # If the env var points to a missing file (like in Cloud Run), 
        # we must unset it so storage.Client() can fall back to IAM/ADC.
        creds_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_env and not os.path.exists(creds_env):
            del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

        # storage.Client() automatically handles the fallback:
        # 1. Environment variable (GOOGLE_APPLICATION_CREDENTIALS) - if valid
        # 2. Attached Service Account (Cloud Run / IAM)
        # 3. Local gcloud credentials
        client = storage.Client(project=project)
        _bucket_ref = client.bucket(bucket_name)
    except Exception as e:
        st.error(f"GCP Init Error: {e}")
        print(f"Warning: Could not initialize GCP client: {e}")
        return None
        
    return _bucket_ref

def get_bq_client():
    global _bq_client
    if _bq_client:
        return _bq_client

    try:
        creds_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_env and not os.path.exists(creds_env):
            del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

        _bq_client = bigquery.Client(project=project)
    except Exception as e:
        st.error(f"BigQuery Init Error: {e}")
        print(f"Warning: Could not initialize BigQuery client: {e}")
        return None
        
    return _bq_client

def uploadJson(data, destination_blob_name, silent=False):
    bucket = get_bucket()
    if not bucket:
        if not silent:
            st.error("GCP not initialized (check credentials)")
        return

    blob = bucket.blob(destination_blob_name)
    try:
        blob.upload_from_string(
            data=json.dumps(data),
            content_type='application/json'
        )
        st.session_state.upload_status = True
    except Exception as e:
        st.session_state.upload_status = False
        st.session_state.upload_error = str(e)
    
    if silent:
        return

    if st.session_state.upload_status:
        st.success("Upload completed successfully!")
        del st.session_state.upload_status
    else:
        st.error(f"Upload failed: {st.session_state.get('upload_error', '')}")
        del st.session_state.upload_status
        st.session_state.pop("upload_error", None)
    return

def listAllSchemas():
    bucket = get_bucket()
    if not bucket: return []
    try:
        blobs = bucket.list_blobs()
        schema_files = [blob.name for blob in blobs if blob.name.endswith('.json')]
        return schema_files
    except Exception as e:
        print(f"Error listing schemas: {e}")
        return []

def readSchemaToJson(schema_name):
    bucket = get_bucket()
    if not bucket: return {}
    try:
        blob = bucket.blob(schema_name)
        schema_data = json.loads(blob.download_as_string())
        return schema_data
    except Exception as e:
        print(f"Error reading schema {schema_name}: {e}")
        return {}

def read_schemas_parallel(schema_names):
    """
    Reads multiple schemas in parallel using ThreadPoolExecutor.
    Returns a dict { schema_name: schema_data }.
    """
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(readSchemaToJson, schema_names))
    
    return dict(zip(schema_names, results))

def readRepoFromJson():
    bucket = get_bucket()
    if not bucket: return {}
    blob = bucket.blob(repo_file_name)

    if not blob.exists():
        empty_json = json.dumps({})
        blob.upload_from_string(empty_json, content_type='application/json', )
        st.info(f"Repo file '{repo_file_name}' not found. Created a new one.")
        return {}

    try:
        raw = blob.download_as_string()
        decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(decoded) if decoded.strip() else {}
    except Exception as e:
        st.error(f"Failed to load repo JSON: {e}")
        return {}

def writeRepoToJson(repo_data):
    bucket = get_bucket()
    if not bucket:
        st.error("GCP not initialized")
        return
    blob = bucket.blob(repo_file_name)
    try:
        blob.upload_from_string(
            data=json.dumps(repo_data),
            content_type='application/json'
        )
        st.success(f"Repository '{repo_file_name}' updated successfully.")
    except Exception as e:
        st.error(f"Failed to write repo JSON: {e}")