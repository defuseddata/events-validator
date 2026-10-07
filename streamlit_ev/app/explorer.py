import streamlit as st
import json
import os
import time
from helpers.storage import (
    list_schemas,
    read_schemas_parallel,
    read_repo,
    write_schema,
    is_github_mode,
    get_current_branch,
    clear_cache,
)
from helpers.components import render_branch_selector, render_storage_status, render_commit_history
from helpers.helpers import readSchemaAndSetState
from helpers.updater import check_schema_health, update_schema_full, render_diff_ui, construct_schema_definition, preserve_schema_customization
import traceback

repo_file_name = os.getenv("REPO_JSON_FILE") or "repo.json"


def render_explorer():
    # Load repo from storage (GitHub or GCS based on config)
    if "repo" not in st.session_state:
        st.session_state.repo = read_repo() or {}

    if st.session_state.get("toast_message"):
        st.success(st.session_state.toast_message)
        st.session_state.toast_message = None

    st.title("Schema Explorer")

    # Branch selector and storage info
    col_branch, col_status = st.columns([2, 3])
    with col_branch:
        if is_github_mode():
            render_branch_selector(key="explorer_branch")
    with col_status:
        render_storage_status()

    # Session-bound Cache Initialization
    if "explorer_cache" not in st.session_state:
        st.session_state.explorer_cache = {
            "schemas": {},      # { schema_name: content }
            "health": {},       # { schema_name: health_dict }
            "last_sync": None,
            "branch": None,     # Track which branch the cache is for
        }

    # Invalidate cache if branch changed
    current_branch = get_current_branch() if is_github_mode() else "main"
    if st.session_state.explorer_cache.get("branch") != current_branch:
        st.session_state.explorer_cache = {
            "schemas": {},
            "health": {},
            "last_sync": None,
            "branch": current_branch,
        }

    # ---------------------------------------------------------
    # CACHE CONTROL
    # ---------------------------------------------------------
    c1, c2 = st.columns([8, 2])
    with c2:
        refresh_label = "Refresh from GitHub" if is_github_mode() else "Refresh from Cloud"
        if st.button(f"{refresh_label}", use_container_width=True):
            clear_cache()
            st.rerun()

    # ---------------------------------------------------------
    # PARALLEL FETCHING & ANALYSIS
    # ---------------------------------------------------------
    if not st.session_state.explorer_cache["schemas"]:
        source = "GitHub" if is_github_mode() else "GCS"
        with st.spinner(f"Fetching and analyzing schemas from {source}..."):
            try:
                all_files = list_schemas()
                filtered = [f for f in all_files if f != repo_file_name]

                # PARALLEL FETCH
                contents = read_schemas_parallel(filtered)

                # BATCH HEALTH CHECK
                health_map = {}
                for f, content in contents.items():
                    health_map[f] = check_schema_health(content, st.session_state.repo)

                st.session_state.explorer_cache["schemas"] = contents
                st.session_state.explorer_cache["health"] = health_map
                st.session_state.explorer_cache["last_sync"] = time.strftime("%H:%M:%S")
                st.session_state.explorer_cache["branch"] = current_branch
            except Exception as e:
                st.error(f"Failed to fetch schemas: {e}")
                traceback.print_exc()
                return

    cache = st.session_state.explorer_cache
    schemas_content = cache["schemas"]
    health_results = cache["health"]

    critical_schemas = [f for f, h in health_results.items() if h.get("critical")]
    minor_only_schemas = [f for f, h in health_results.items() if h.get("minor") and not h.get("critical")]

    # ---------------------------------------------------------
    # BULK SYNC UTILITY
    # ---------------------------------------------------------
    minor_impacted = {f: h for f, h in health_results.items() if h.get("minor")}

    with st.expander("Bulk Sync Utility (Minor Updates)", expanded=False):
        if not minor_impacted:
            st.success("All schemas are in sync with the repository metadata!")
        else:
            st.write(f"Found {len(minor_impacted)} schema(s) with Minor mismatches.")

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
                if st.button("Sync Selected Schemas", type="primary"):
                    success_count = 0
                    with st.spinner("Syncing..."):
                        for s_name in sync_selection.keys():
                            success, _ = update_schema_full(s_name, st.session_state.repo)
                            if success:
                                success_count += 1

                    st.success(f"Successfully synced metadata for {success_count} schema(s)!")
                    # Clear cache to force re-scan
                    clear_cache()
                    time.sleep(1)
                    st.rerun()

    # ---------------------------------------------------------
    # SCHEMA LIST
    # ---------------------------------------------------------
    source_label = f"GitHub ({current_branch})" if is_github_mode() else "GCP Bucket"
    st.markdown(f"## Available Schemas in {source_label}")
    status_parts = []
    if critical_schemas:
        status_parts.append(f":red[{len(critical_schemas)} schema(s) with critical errors]")
    if minor_only_schemas:
        status_parts.append(f":orange[{len(minor_only_schemas)} schema(s) with minor errors]")
    if status_parts:
        st.markdown("&nbsp;&nbsp;&nbsp;".join(status_parts))

    if not schemas_content:
        st.info("No schemas found. Create a schema in the Builder or add files to the repository.")
        return

    available_categories = sorted({
        param.get("category", "Uncategorized")
        for param in st.session_state.repo.values()
        if param.get("category")
    })

    col_sync, col_filter, col_category, col_search = st.columns([2, 2, 2, 3], vertical_alignment="center")
    with col_sync:
        if cache["last_sync"]:
            st.caption(f"Last sync: {cache['last_sync']}")
    with col_filter:
        status_filter = st.selectbox(
            "Filter by status",
            ["All Statuses", "Critical", "Minor", "Healthy"],
            key="explorer_status_filter",
            label_visibility="collapsed",
        )
    with col_category:
        has_uncategorized = any(not param.get("category") for param in st.session_state.repo.values())
        category_filter = st.selectbox(
            "Filter by category",
            ["All Categories"] + ([""] if has_uncategorized else []) + available_categories,
            key="explorer_category_filter",
            label_visibility="collapsed",
            format_func=lambda c: "— No category —" if c == "" else c,
        )
    with col_search:
        query = st.text_input(
            "Search schema",
            key="explorer_search",
            label_visibility="collapsed",
            placeholder="Search schema",
        )

    # Show commit history if in GitHub mode
    if is_github_mode():
        with st.expander("Recent Changes", expanded=False):
            render_commit_history(limit=5)

    def schema_status(health):
        if health.get("critical"):
            return "Critical"
        if health.get("minor"):
            return "Minor"
        return "Healthy"

    def schema_categories(content):
        return {
            st.session_state.repo[param_name].get("category") or ""
            for param_name in content
            if param_name not in ("event_name", "version") and param_name in st.session_state.repo
        }

    filtered_schemas = sorted(schemas_content.items())
    if query:
        filtered_schemas = [
            (schema_file, content)
            for schema_file, content in filtered_schemas
            if query.lower() in schema_file.lower()
        ]
    if status_filter != "All Statuses":
        filtered_schemas = [
            (schema_file, content)
            for schema_file, content in filtered_schemas
            if schema_status(health_results.get(schema_file, {})) == status_filter
        ]
    if category_filter != "All Categories":
        filtered_schemas = [
            (schema_file, content)
            for schema_file, content in filtered_schemas
            if category_filter in schema_categories(content)
        ]
    if not filtered_schemas:
        st.info("No schemas match the current filters.")

    for schema_file, content in filtered_schemas:
        health = health_results.get(schema_file, {})
        crit = health.get("critical", [])
        minor = health.get("minor", [])

        spacer = "&nbsp;&nbsp;&nbsp;&nbsp;"
        if crit:
            label = f"{schema_file}{spacer}:red-background[CRITICAL ({len(crit)})]"
        elif minor:
            label = f"{schema_file}{spacer}:orange-background[Minor ({len(minor)})]"
        else:
            label = schema_file

        with st.expander(label):
            st.write(f"Schema File: {schema_file}")

            if crit:
                st.error(f"CRITICAL: Type mismatches in: {', '.join(crit)}. Sync required!")
                with st.expander("Review Critical Mismatches", expanded=False):
                    for p in crit:
                        if p in st.session_state.repo:
                            st.markdown(f"**Parameter: `{p}` (TYPE MISMATCH)**")
                            repo_param = st.session_state.repo[p]
                            new_props = construct_schema_definition(repo_param)
                            new_props = preserve_schema_customization(content.get(p, {}), new_props)
                            render_diff_ui(content, {p: new_props}, p)
                            st.markdown("---")
            if minor:
                st.warning(f"Minor updates available: {', '.join(minor)}")
                with st.expander("Review Differences", expanded=False):
                    for p in minor:
                        if p in st.session_state.repo:
                            st.markdown(f"**Parameter: `{p}`**")
                            repo_param = st.session_state.repo[p]
                            # Construct what the new props would look like —
                            # mirror update_schema_full's own preserve logic
                            # so the preview matches what Sync with Repo
                            # will actually do.
                            new_props = construct_schema_definition(repo_param)
                            new_props = preserve_schema_customization(content.get(p, {}), new_props)
                            # Show side-by-side diff
                            render_diff_ui(content, {p: new_props}, p)
                            st.markdown("---")

            if crit or minor:
                if st.button("Sync with Repo", key=f"fix-{schema_file}"):
                    success, msgs = update_schema_full(schema_file, st.session_state.repo)
                    if success:
                        st.success("Schema updated!")
                        clear_cache()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Update failed: {msgs}")

            st.json(content, expanded=False)
            if st.button("Edit Schema", key=f"edit-{schema_file}", on_click=readSchemaAndSetState, args=(content,)):
                pass
