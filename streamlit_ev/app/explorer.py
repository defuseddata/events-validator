import streamlit as st
import json
import os
from helpers.gcp import listAllSchemas, readSchemaToJson, readRepoFromJson
from helpers.helpers import readSchemaAndSetState
from helpers.updater import check_schema_health, update_schema_full
import traceback
import time

repo_file_name = os.getenv("REPO_JSON_FILE") or "repo.json"

def render_explorer():
    if "repo" not in st.session_state:
        st.session_state.repo = readRepoFromJson() or {}

    if st.session_state.get("toast_message"):
        st.success(st.session_state.toast_message)
        st.session_state.toast_message = None
    st.title("Schema Explorer")
    st.header("Available Schemas in GCP Bucket")

    bucket = os.getenv("BUCKET_NAME")

    with st.spinner("Wait for it...", show_time=True):
        try:
            schema_files = listAllSchemas()

            if not schema_files:
                st.info("No schema files found in the bucket.")
                return
            filtered_files = [
                f for f in schema_files
                if f != repo_file_name
            ]

            if not filtered_files:
                st.info("No schema files found")
                return

            st.success(f"Found {len(filtered_files)} schema files.")
            for schema_file in filtered_files:
                # Load content first to check health
                schema_content = readSchemaToJson(schema_file)
                
                # Health Check
                outdated_params = check_schema_health(schema_content, st.session_state.repo)
                
                label = schema_file
                if outdated_params:
                    label += f" ⚠️ ({len(outdated_params)} outdated)"
                
                with st.expander(label):
                    st.write(f"Schema File: {schema_file}")
                    st.text(f"Located in bucket: {bucket}")
                    
                    if outdated_params:
                        st.warning(f"This schema differs from the repository in parameters: {', '.join(outdated_params)}")
                        if st.button("🔄 Update Schema from Repo", key=f"fix-{schema_file}"):
                             success, msgs = update_schema_full(schema_file, st.session_state.repo)
                             if success:
                                 st.success("Schema updated successfully!")
                                 time.sleep(1)
                                 st.rerun()
                             else:
                                 st.error(f"Update failed: {msgs}")
                    
                    st.json(schema_content, expanded=False)

                    cols = st.columns([1, 3])
                    cols[0].button(
                        "Edit Schema",
                        key=f"edit-{schema_file}",
                        on_click=readSchemaAndSetState,
                        args=(schema_content,)
                    )


        except Exception as e:
            st.error(f"An error occurred while fetching schemas:")
            st.error(traceback.format_exc())
