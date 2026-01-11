import streamlit as st
import json
import os
from helpers.gcp import listAllSchemas, readSchemaToJson, readRepoFromJson, read_schemas_parallel
from helpers.helpers import readSchemaAndSetState
from helpers.updater import check_schema_health, update_schema_full, render_diff_ui, construct_schema_definition
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
    
    # Session-bound Cache Initialization
    if "explorer_cache" not in st.session_state:
        st.session_state.explorer_cache = {
            "schemas": {},      # { schema_name: content }
            "health": {},       # { schema_name: health_dict }
            "last_sync": None
        }

    # ---------------------------------------------------------
    # CACHE CONTROL
    # ---------------------------------------------------------
    c1, c2 = st.columns([8, 2])
    with c2:
        if st.button("🔄 Refresh from Cloud", use_container_width=True):
            st.session_state.explorer_cache = {"schemas": {}, "health": {}, "last_sync": None}
            st.rerun()

    # ---------------------------------------------------------
    # PARALLEL FETCHING & ANALYSIS
    # ---------------------------------------------------------
    if not st.session_state.explorer_cache["schemas"]:
        with st.spinner("Fetching and analyzing schemas in parallel..."):
            try:
                all_files = listAllSchemas()
                filtered = [f for f in all_files if f != repo_file_name]
                
                # PARALLEL FETCH 🚀
                contents = read_schemas_parallel(filtered)
                
                # BATCH HEALTH CHECK
                health_map = {}
                for f, content in contents.items():
                    health_map[f] = check_schema_health(content, st.session_state.repo)
                
                st.session_state.explorer_cache["schemas"] = contents
                st.session_state.explorer_cache["health"] = health_map
                st.session_state.explorer_cache["last_sync"] = time.strftime("%H:%M:%S")
            except Exception as e:
                st.error(f"Failed to fetch schemas: {e}")
                return

    cache = st.session_state.explorer_cache
    schemas_content = cache["schemas"]
    health_results = cache["health"]
    
    # ---------------------------------------------------------
    # BULK SYNC UTILITY
    # ---------------------------------------------------------
    minor_impacted = {f: h for f, h in health_results.items() if h.get("minor")}
    
    with st.expander("🚀 Bulk Sync Utility (Minor Updates)", expanded=False):
        if not minor_impacted:
            st.success("All schemas are in sync with the repository metadata!")
        else:
            st.write(f"Found {len(minor_impacted)} schema(s) with 🟡 Minor mismatches.")
            
            # Group by affected param
            affected_by_param = {}
            for f, h in minor_impacted.items():
                for p in h["minor"]:
                    affected_by_param.setdefault(p, []).append(f)
            
            st.markdown("#### Select parameters to sync:")
            sync_selection = {}
            for param, schemas in sorted(affected_by_param.items()):
                is_sel = st.checkbox(f"Parameter: `{param}` ({len(schemas)} schemas affected)", value=True, key=f"bulk_sync_{param}")
                if is_sel:
                    for s in schemas:
                        sync_selection.setdefault(s, []).append(param)
            
            if sync_selection:
                if st.button("🚀 Sync Selected Schemas", type="primary"):
                    success_count = 0
                    with st.spinner("Syncing..."):
                        for s_name in sync_selection.keys():
                            success, _ = update_schema_full(s_name, st.session_state.repo)
                            if success: success_count += 1
                    
                    st.success(f"Successfully synced metadata for {success_count} schema(s)!")
                    # Clear cache to force re-scan
                    st.session_state.explorer_cache = {"schemas": {}, "health": {}, "last_sync": None}
                    time.sleep(1)
                    st.rerun()
    # ---------------------------------------------------------

    st.header("Available Schemas in GCP Bucket")
    if cache["last_sync"]:
        st.caption(f"Last sync with GCS: {cache['last_sync']}")

    for schema_file, content in sorted(schemas_content.items()):
        health = health_results.get(schema_file, {})
        crit = health.get("critical", [])
        minor = health.get("minor", [])
        
        label = schema_file
        if crit: label += f" 🔴 CRITICAL ({len(crit)})"
        elif minor: label += f" 🟡 Minor ({len(minor)})"
        
        with st.expander(label):
            st.write(f"Schema File: {schema_file}")
            
            if crit:
                 st.error(f"CRITICAL: Type mismatches in: {', '.join(crit)}. Sync required!")
                 with st.expander("🚨 Review Critical Mismatches", expanded=False):
                    for p in crit:
                        if p in st.session_state.repo:
                            st.markdown(f"**Parameter: `{p}` (TYPE MISMATCH)**")
                            repo_param = st.session_state.repo[p]
                            new_props = construct_schema_definition(repo_param)
                            render_diff_ui(content, {p: new_props}, p)
                            st.markdown("---")
            if minor:
                st.warning(f"Minor updates available: {', '.join(minor)}")
                with st.expander("🔍 Review Differences", expanded=False):
                    for p in minor:
                        if p in st.session_state.repo:
                            st.markdown(f"**Parameter: `{p}`**")
                            repo_param = st.session_state.repo[p]
                            # Construct what the new props would look like
                            new_props = construct_schema_definition(repo_param)
                            # Show side-by-side diff
                            render_diff_ui(content, {p: new_props}, p)
                            st.markdown("---")
            
            if crit or minor:
                if st.button("🔄 Sync with Repo", key=f"fix-{schema_file}"):
                     success, msgs = update_schema_full(schema_file, st.session_state.repo)
                     if success:
                         st.success("Schema updated!")
                         st.session_state.explorer_cache = {"schemas": {}, "health": {}, "last_sync": None}
                         time.sleep(1)
                         st.rerun()
                     else:
                         st.error(f"Update failed: {msgs}")
            
            st.json(content, expanded=False)
            if st.button("Edit Schema", key=f"edit-{schema_file}", on_click=readSchemaAndSetState, args=(content,)):
                pass
