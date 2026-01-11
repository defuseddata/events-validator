import time
import pandas as pd
import streamlit as st
import json
import os
import copy
from helpers.gcp import readRepoFromJson, writeRepoToJson, read_schemas_parallel
from helpers.helpers import render_field_row, pretty_schema_inline
from helpers.updater import (
    find_impacted_schemas, 
    apply_updates, 
    render_diff_ui, 
    construct_schema_definition,
    update_schema_full,
    check_schema_health
)
from dotenv import load_dotenv

load_dotenv()

repo_file_name = os.getenv("REPO_JSON_FILE") or "repo.json"
typeOptions = ["string", "number", "boolean", "array"]

def clean_repo_types(repo):
    """Ensures numeric values are stored as numbers, not strings."""
    for param in repo.values():
        if param.get("type") == "number" and "value" in param:
            val = param["value"]
            if isinstance(val, str) and val.strip() != "":
                try:
                    param["value"] = float(val) if "." in val else int(val)
                except: pass
        
        if param.get("type") == "array" and "nestedSchema" in param:
            for n_param in param["nestedSchema"].values():
                if n_param.get("type") == "number" and "value" in n_param:
                    n_val = n_param["value"]
                    if isinstance(n_val, str) and n_val.strip() != "":
                        try:
                            n_param["value"] = float(n_val) if "." in n_val else int(n_val)
                        except: pass
    return repo

def ensure_repo_loaded():
    if "repo" not in st.session_state:
        repo = readRepoFromJson() or {}
        st.session_state.repo = clean_repo_types(repo)

# available_categories = sorted({param.get("category", "Uncategorized") for param in st.session_state.repo.values()})
def get_available_categories():
    return sorted({
        param.get("category", "Uncategorized")
        for param in st.session_state.get("repo", {}).values()
        if param.get("category")
    })


# RENDER REPO

def render_repo():
    ensure_repo_loaded()
    if "show_new_param_builder" not in st.session_state:
        st.session_state.show_new_param_builder = False

    col = st.columns([1, 1])
    with col[0]:
        st.title("Parameters Repository")
        if st.button("➕ Add new parameter", type="primary"):
            myfn(next_id_for_repo())

    # Load repo
    # repo_data = readRepoFromJson()
    # st.session_state.repo = repo_data
    # available_categories = sorted({param.get("category", "Uncategorized") for param in st.session_state.repo.values()})

    # CHECK FOR PENDING CONFIRMATION (To avoid nested dialogs)
    if "pending_confirmation" in st.session_state:
        data = st.session_state.pending_confirmation
        st.warning(f"Update pending for parameter '{data['param_name']}'. Please review impacts.")
        if st.button("Review & Confirm Updates", type="primary"):
            confirm_update_dialog(data["map"], data["param_name"])


    with col[1]:
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.header(f"Total parameters: {len(st.session_state.repo)}")
        # st.session_state.show_new_param_builder = not st.session_state.get("show_new_param_builder", False)
    repo = st.session_state.repo
    if not repo:
        st.info("Repository is empty. Add the first parameter!")
    else:
        for name, param in repo.items():
            category = param.get("category", "Uncategorized")
            param_type = param.get("type", "Undefined")

            exp_label = (
                f"{name}   |   "
                f"category: {category}   |   "
                f"type: {param_type}"
            )

            with st.expander(exp_label, expanded=False):
                cols = st.columns([2,2])

                table = pd.DataFrame([
                    ["Type", str(param.get("type", ""))],
                    ["Default Value", str(param.get("value", ""))],
                    ["Category", str(param.get("category", ""))],
                    ["Description", str(param.get("description", ""))],
                    ["Used In", json.dumps(param.get("usedInSchemas", ""))],
                ], columns=["Field", "Value"])

                with cols[0]:
                    st.table(table.set_index("Field"))
                with cols[1]:
                    st.json(param, expanded=False)
                if st.button("Edit", key=f"button-test-{name}"):
                    edit_param_dialog(name)

    # Show builder
    if st.session_state.get("show_new_param_builder", False):
        st.subheader("Parameter Creator")

        if st.button("❌ Cancel parameter", key="cancel_new_param"):
            st.session_state.show_new_param_builder = False
            # cleanup stanu buildera
            for key in list(st.session_state.keys()):
                if key.startswith("repo_") or key.startswith("custom_cat_"):
                    del st.session_state[key]

            st.session_state.pop("new_nested", None)

            st.rerun()


# HELPERS

def repoToState(repoinJson):
    repoData = json.loads(repoinJson)
    st.session_state.repo = repoData
    st.session_state.toast_message = "Repository loaded successfully."


def stateToRepo():
    repoData = st.session_state.get("repo", {})
    writeRepoToJson(repoData)


def addParamToRepo(param):
    param = param.strip()
    if not param:
        return
    repo = st.session_state.get("repo", {})
    if param in repo:
        st.warning(f"Parameter '{param}' already exists in the repository.")
        return
    repo[param] = {"type": "string", "value": ""}
    st.session_state.repo = repo
    st.session_state.toast_message = f"Parameter '{param}' added to repository."

def sync_explorer_cache(updated_schemas_map=None):
    """
    Granularly updates the session-bounded Explorer cache after a repo change.
    - If schemas were updated on GCP, we update their cached JSON content.
    - We re-run health checks on all cached schemas against the new repo state.
    """
    if "explorer_cache" not in st.session_state:
        return
    
    cache = st.session_state.explorer_cache
    repo = st.session_state.get("repo", {})
    
    # 1. Update cached schema contents if we just modified them
    if updated_schemas_map:
        for s_name, data_container in updated_schemas_map.items():
            # data_container is usually {"original":..., "new":...}
            new_content = data_container.get("new", data_container)
            if s_name in cache["schemas"]:
                cache["schemas"][s_name] = new_content

    # 2. Re-run health checks on ALL cached schemas (Fast local operation)
    new_health = {}
    for f, content in cache["schemas"].items():
        new_health[f] = check_schema_health(content, repo)
    
    cache["health"] = new_health
    st.session_state.explorer_cache = cache


def next_id_for_repo():
    repo = st.session_state.get("repo", {})
    return len(repo)

# PARAMETER BUILDER

def delete_nested(nid):
    del st.session_state.new_nested[nid]


def add_nested():
    if "new_nested" not in st.session_state:
        st.session_state.new_nested = {}
    
    nested = st.session_state.new_nested
    next_id = max(nested.keys(), default=-1) + 1
    nested[next_id] = {
        "key": "", 
        "type": "string", 
        "value": "", 
        "description": ""
    }


def add_nested_edit(param_name):
    key = f"edit_nested_{param_name}"
    if key not in st.session_state:
        st.session_state[key] = {}
    
    nested = st.session_state[key]
    next_id = max(nested.keys(), default=-1) + 1
    nested[next_id] = {
        "key": "", 
        "type": "string", 
        "value": "", 
        "description": ""
    }

def delete_nested_edit(param_name, nid):
    key = f"edit_nested_{param_name}"
    if key in st.session_state and nid in st.session_state[key]:
        del st.session_state[key][nid]


    name = cols[0].text_input("Parameter name", key=f"repo_key_{param_id}")
    type_val = cols[1].selectbox(
        "Type",
        typeOptions,
        key=f"repo_type_{param_id}"
    )
    # Category selection
    category = cols[2].selectbox(
        "Category",
        get_available_categories(),
        key=f"repo_cat_{param_id}",
        accept_new_options=True,
        placeholder="choose or fill in new category"
    )

    # If user selects Custom → show text input
    # if category == "Custom":
    #     custom_value = cols[2].text_input(
    #         "Custom category",
    #         placeholder="Enter custom category name",
    #         key=f"custom_cat_{param_id}"
    #     )
    #     category = custom_value or "Custom"

    value = None
    if type_val == "boolean":
        value = cols[3].selectbox("Default Value", key=f"repo_val_{param_id}", options=["true", "false", "Any"])
    elif type_val == "number":
        value = cols[3].text_input("Default Value (number)", key=f"repo_val_{param_id}", placeholder="e.g. 1.0 or leave empty")
    elif type_val != "array":
        value = cols[3].text_input("Default Value", key=f"repo_val_{param_id}")
    else:
        st.info(f"Now You are creating an Array parameter: {name or 'no name'}. Add nested fields below:")


    description = cols[4].text_area(
        "Description",
        key=f"repo_desc_{param_id}",
        placeholder="Describe what this parameter means, how it's used, constraints, notes…"
    )

def add_bulk_param():
    if "bulk_params" not in st.session_state:
        st.session_state.bulk_params = {}
    
    new_id = max(st.session_state.bulk_params.keys(), default=-1) + 1
    st.session_state.bulk_params[new_id] = {
        "name": "",
        "type": "string",
        "category": "",
        "mode": "Value",
        "value": "",
        "regex": "",
        "description": "",
        "nested": {} # For array type
    }

def delete_bulk_param(pid):
    if "bulk_params" in st.session_state and pid in st.session_state.bulk_params:
        del st.session_state.bulk_params[pid]

def add_nested_bulk(pid):
    if "bulk_params" in st.session_state and pid in st.session_state.bulk_params:
        nested = st.session_state.bulk_params[pid]["nested"]
        new_nid = max(nested.keys(), default=-1) + 1
        nested[new_nid] = {
            "key": "",
            "type": "string",
            "mode": "Value",
            "value": "",
            "regex": "",
            "description": ""
        }

def delete_nested_bulk(pid, nid):
    if "bulk_params" in st.session_state and pid in st.session_state.bulk_params:
        nested = st.session_state.bulk_params[pid]["nested"]
        if nid in nested:
            del nested[nid]

def newParamBuilder(param_id):

    alert = ("Fill in the details below to add new parameters.")
    st.info(alert)
    st.subheader("New parameters")       

    # Initialize bulk_params if not present
    if "bulk_params" not in st.session_state or not st.session_state.bulk_params:
        st.session_state.bulk_params = {}
        add_bulk_param() # Add first one

    # Iterate over bulk params
    params_to_render = sorted(st.session_state.bulk_params.items())
    
    for pid, p_data in params_to_render:
        with st.container():
            st.markdown(f"#### Parameter #{pid + 1}")
            cols = st.columns([3, 2, 2, 2, 2, 4, 1])

            p_data["name"] = cols[0].text_input("Name", p_data["name"], key=f"bp_name_{pid}")
            p_data["type"] = cols[1].selectbox("Type", typeOptions, key=f"bp_type_{pid}", index=typeOptions.index(p_data["type"]) if p_data["type"] in typeOptions else 0)
            
            p_data["category"] = cols[2].selectbox(
                "Category",
                get_available_categories(),
                key=f"bp_cat_{pid}",
                accept_new_options=True,
                index=get_available_categories().index(p_data["category"]) if p_data["category"] in get_available_categories() else 0,
                placeholder="choose..."
            )

            if p_data["type"] != "array":
                p_data["mode"] = cols[3].selectbox("Validation", ["Value", "Regex"], key=f"bp_mode_{pid}", index=0 if p_data["mode"] == "Value" else 1)
                
                if p_data["mode"] == "Value":
                    if p_data["type"] == "boolean":
                         p_data["value"] = cols[4].selectbox("Value", ["true", "false", "Any"], key=f"bp_val_{pid}", index=["true", "false", "Any"].index(str(p_data["value"]).lower()) if str(p_data["value"]).lower() in ["true", "false", "Any"] else 2)
                    elif p_data["type"] == "number":
                         p_data["value"] = cols[4].number_input("Value", value=float(p_data["value"]) if p_data["value"] else 0.0, key=f"bp_val_{pid}")
                    else:
                         p_data["value"] = cols[4].text_input("Value", p_data["value"], key=f"bp_val_{pid}")
                else:
                    p_data["regex"] = cols[4].text_input("Regex", p_data["regex"], key=f"bp_regex_{pid}")
            else:
                cols[3].markdown("—")
                cols[4].markdown("—")
            
            p_data["description"] = cols[5].text_area("Description", p_data["description"], key=f"bp_desc_{pid}", height=68)
            
            if len(st.session_state.bulk_params) > 1:
                cols[6].button("🗑️", key=f"bp_del_{pid}", on_click=delete_bulk_param, args=(pid,))

            # Nested fields for Array
            if p_data["type"] == "array":
                with st.expander(f"Nested fields for '{p_data['name']}'", expanded=True):
                    nested_items = sorted(p_data["nested"].items())
                    for nid, nf in nested_items:
                        r = st.columns([3, 2, 2, 2, 1])
                        nf["key"] = r[0].text_input("Key", nf["key"], key=f"bp_n_key_{pid}_{nid}")
                        nf["type"] = r[1].selectbox("Type", ["string", "number", "boolean"], key=f"bp_n_type_{pid}_{nid}", index=["string", "number", "boolean"].index(nf["type"]))
                        
                        nf["mode"] = r[2].selectbox("Validation", ["Value", "Regex"], key=f"bp_n_mode_{pid}_{nid}", index=0 if nf.get("mode", "Value") == "Value" else 1)
                        
                        if nf["mode"] == "Value":
                            if nf["type"] == "boolean":
                                nf["value"] = r[3].selectbox("Value", ["true", "false", "Any"], key=f"bp_n_val_{pid}_{nid}", index=["true", "false", "Any"].index(str(nf.get("value", "Any")).lower()) if str(nf.get("value", "Any")).lower() in ["true", "false", "Any"] else 2)
                            elif nf["type"] == "number":
                                nf["value"] = r[3].number_input("Value", value=float(nf.get("value", 0)) if nf.get("value") else 0.0, key=f"bp_n_val_{pid}_{nid}")
                            else:
                                nf["value"] = r[3].text_input("Value", nf.get("value", ""), key=f"bp_n_val_{pid}_{nid}")
                        else:
                            nf["regex"] = r[3].text_input("Regex", nf.get("regex", ""), key=f"bp_n_regex_{pid}_{nid}")

                        r[4].button("❌", key=f"bp_n_del_{pid}_{nid}", on_click=delete_nested_bulk, args=(pid, nid))
                        nf["description"] = st.text_area("Description", nf.get("description", ""), key=f"bp_n_desc_{pid}_{nid}", height=68)
                        st.divider()
                    
                    st.button("➕ Add nested key", key=f"bp_n_add_{pid}", on_click=add_nested_bulk, args=(pid,))

            st.markdown("---")

    st.button("➕ Add another parameter", on_click=add_bulk_param)

    st.markdown("---")
    # SAVE PARAMETER
    if st.button("Save All Parameters", type="primary"):
        repo = st.session_state.get("repo", {})
        saved_count = 0
        errors = []

        for pid, p_data in st.session_state.bulk_params.items():
            name = p_data["name"].strip()
            if not name:
                continue # Skip empty names

            if name in repo:
                errors.append(f"Parameter '{name}' already exists.")
                continue

            new_param = {
                "type": p_data["type"],
                "category": p_data["category"],
                "description": p_data["description"]
            }

            if p_data["type"] == "array":
                constructed_nested = {}
                for nf in p_data["nested"].values():
                    k = nf["key"].strip()
                    if k:
                        item = {
                            "type": nf["type"],
                            "description": nf.get("description", "")
                        }
                        if nf["mode"] == "Value":
                             val = nf.get("value")
                             if nf["type"] == "number" and isinstance(val, str) and val.strip() != "":
                                  try: val = float(val) if "." in val else int(val)
                                  except: pass
                             item["value"] = val
                        else:
                             item["regex"] = nf.get("regex")
                        constructed_nested[k] = item
                new_param["nestedSchema"] = constructed_nested
            else:
                if p_data["mode"] == "Value":
                    val = p_data["value"]
                    if p_data["type"] == "number" and isinstance(val, str) and val.strip() != "":
                        try: val = float(val) if "." in val else int(val)
                        except: pass
                    new_param["value"] = val
                else:
                    new_param["regex"] = p_data["regex"]
            
            repo[name] = new_param
            saved_count += 1

        if errors:
            for err in errors:
                st.error(err)
        
        if saved_count > 0:
            st.session_state.repo = repo
            writeRepoToJson(repo)
            st.success(f"Successfully added {saved_count} parameters.")
            # Clear bulk params
            st.session_state.bulk_params = {}
            time.sleep(2)
            st.rerun()
        elif not errors:
             st.warning("No valid parameters to save.")

def paramEditor(param):
    with st.dialog(title="test"):
        st.button("test")
        st.json(param)

@st.dialog("Confirm Schema Updates", width="large")
def confirm_update_dialog(full_schema_map, param_name):
    # Retrieve draft data from session state (passed implicitly via pending_confirmation logic)
    # The caller unpacks map and param_name, but we might need to access the full object if we didn't pass it.
    # To keep signatures clean, let's grab it from session state directly if needed, OR relies on caller passing it?
    # The calling code in render_repo is: confirm_update_dialog(data["map"], data["param_name"])
    # We should update call site too? Or just use session state here? using session state is easier given the context.
    
    draft_data = st.session_state.pending_confirmation.get("draft_param_data")
    
    st.warning(f"Parameter '{param_name}' is used in {len(full_schema_map)} deployed schema(s).")
    st.markdown("Select which schemas to update:")

    # MASTER TOGGLE
    def toggle_all():
        b_val = st.session_state.master_toggle_schemas
        for s_name in full_schema_map.keys():
            st.session_state[f"chk_{s_name}"] = b_val

    st.checkbox("Select / Deselect all schemas", value=True, key="master_toggle_schemas", on_change=toggle_all)
    
    # Selection State initialization
    selected_schemas = []
    
    # We need keys for checkboxes.
    for schema_name, data in full_schema_map.items():
        # Checkbox for each schema
        # Use a container to group checkbox and expander
        c1, c2 = st.columns([0.1, 0.9])
        with c1:
            # use master toggle as default if state not set
            def_val = st.session_state.get("master_toggle_schemas", True)
            is_checked = st.checkbox("Select Schema", value=def_val, key=f"chk_{schema_name}", label_visibility="collapsed")
            if is_checked:
                selected_schemas.append(schema_name)
        with c2:
            with st.expander(f"Review: {schema_name}", expanded=False):
                render_diff_ui(data["original"], data["new"], param_name)
    
    # ---------------------------------------------------------
    # CLEANUP HELPER
    def cleanup_confirmation():
        if "pending_confirmation" in st.session_state:
            del st.session_state.pending_confirmation
        if "master_toggle_schemas" in st.session_state:
            del st.session_state.master_toggle_schemas
        for k in list(st.session_state.keys()):
            if k.startswith("chk_"):
                del st.session_state[k]

    st.markdown("---")
    col1, col2 = st.columns([1,1])
    
    with col1:
        if st.button("Cancel"):
            cleanup_confirmation()
            st.rerun()
            
    with col2:
        if st.button("Confirm & Update", type="primary"):
            # 1. Update Selected Schemas on GCP
            updates_only = {name: full_schema_map[name]["new"] for name in selected_schemas}
            
            success_count = 0
            if updates_only:
                success, errors = apply_updates(updates_only)
                success_count = success
                if errors:
                    st.error(f"Schema Update Errors: {errors}")
                
            # 2. Update Local Repo (Atomic Commit)
            if draft_data:
                st.session_state.repo[param_name] = draft_data
                writeRepoToJson(st.session_state.repo)
                st.toast("Repository updated.")

            if success_count > 0:
                st.success(f"Updated {success_count} schema(s) successfully!")
            
            # GRANULAR CACHED SYNC 🧠
            sync_explorer_cache(updates_only)
            
            cleanup_confirmation()
            time.sleep(2)
            st.rerun()

@st.dialog("Edit parameter", width="large")
def edit_param_dialog(param_name):
    st.header(param_name)
    param = st.session_state.repo[param_name]
    
    nested_state_key = f"edit_nested_{param_name}"
    
    if nested_state_key not in st.session_state:
        st.session_state[nested_state_key] = {}
        if param.get("type") == "array" and "nestedSchema" in param:
            ns = param["nestedSchema"]
            for i, (k, v) in enumerate(ns.items()):
                 st.session_state[nested_state_key][i] = {
                     "key": k,
                     "type": v.get("type", "string"),
                     "value": v.get("value", ""),
                     "regex": v.get("regex", ""),
                     "description": v.get("description", "")
                 }

    current_value = param.get("value", "")
    current_regex = param.get("regex", "")
    current_type = param.get("type", "string")
    current_type_index = typeOptions.index(current_type) if current_type in typeOptions else 0
    current_category = param.get("category", "")
    current_cat_index = get_available_categories().index(current_category) if current_category in get_available_categories() else 0
    current_description = param.get("description", "")

    new_type = st.selectbox(
        "Type",
        typeOptions,
        key=f"edit-{param_name}-type",
        index=current_type_index,
    )
    
    new_value = None
    new_regex = None
    if new_type != "array":
        mode = st.radio("Validation Type", ["Fixed Value", "Regex Pattern"], 
                        index=1 if current_regex else 0, horizontal=True,
                        key=f"edit-{param_name}-mode")
        
        if mode == "Fixed Value":
            if new_type == "boolean":
                opts = ["true", "false", "Any"]
                cv_str = str(current_value).lower()
                curr_val_idx = opts.index(cv_str) if cv_str in opts else 2
                new_value = st.selectbox("Value", opts, index=curr_val_idx, key=f"edit_{param_name}-value-bool")
            elif new_type == "number":
                try:
                    curr_num = float(current_value) if current_value else 0.0
                except:
                    curr_num = 0.0
                new_value = st.number_input("Value", value=curr_num, key=f"edit_{param_name}-value-num")
            else:
                new_value = st.text_input(
                    "Value",
                    value=current_value if current_value else "",
                    key=f"edit_{param_name}-value"
                )
        else:
            new_regex = st.text_input("Regex Pattern", value=current_regex, key=f"edit_{param_name}-regex")
    else:
        st.caption("Nested fields for Array:")
        edit_nested = st.session_state[nested_state_key]
        
        for nid, nf in edit_nested.items():
            r = st.columns([3, 2, 2, 2, 1])
            nf["key"] = r[0].text_input("Key", nf.get("key", ""), key=f"ed_nk_{param_name}_{nid}")
            nf["type"] = r[1].selectbox("Type", ["string", "number", "boolean"], index=["string", "number", "boolean"].index(nf.get("type", "string")), key=f"ed_nt_{param_name}_{nid}")
            
            nest_mode = r[2].selectbox("Validation", ["Value", "Regex"], key=f"ed_mode_{param_name}_{nid}", index=1 if nf.get("regex") else 0)
            if nest_mode == "Value":
                if nf["type"] == "boolean":
                     opts = ["true", "false", "Any"]
                     cval = str(nf.get("value", "Any")).lower()
                     cidx = opts.index(cval) if cval in opts else 2
                     nf["value"] = r[3].selectbox("Value", opts, index=cidx, key=f"ed_nv_{param_name}_{nid}")
                elif nf["type"] == "number":
                     nf["value"] = r[3].number_input("Value", value=float(nf.get("value", 0)) if nf.get("value") else 0.0, key=f"ed_nv_{param_name}_{nid}")
                else:
                     nf["value"] = r[3].text_input("Value", nf.get("value", ""), key=f"ed_nv_{param_name}_{nid}")
                nf.pop("regex", None)
            else:
                nf["regex"] = r[3].text_input("Regex Pattern", nf.get("regex", ""), key=f"ed_nr_{param_name}_{nid}")
                nf.pop("value", None)
                 
            r[4].button("❌", key=f"ed_del_{param_name}_{nid}", on_click=delete_nested_edit, args=(param_name, nid))
            nf["description"] = st.text_area("Description", nf.get("description", ""), key=f"ed_nd_{param_name}_{nid}", height=68)
            st.markdown("---")
            
        st.button("➕ Add nested key", key=f"ed_add_{param_name}", on_click=add_nested_edit, args=(param_name,))

    new_category = st.selectbox(
        "Category",
        options=get_available_categories(),
        key=f"edit-{param_name}-category",
        index=current_cat_index, 
    )
    new_description = st.text_area(
        "Description",
        key=f"edit-{param_name}-description",
        value=current_description,
        placeholder="Describe what this parameter means, how it's used, constraints, notes…"
    )
    
    # TYPE CHANGE RESET LOGIC
    if new_type != current_type:
        st.info(f"💡 Type changed from `{current_type}` to `{new_type}`. Default value will be reset to a safe type-compliant placeholder upon saving.")
        if new_type == "number": new_value = 0
        elif new_type == "boolean": new_value = "Any"
        elif new_type == "array": new_value = None
        else: new_value = ""

    if st.button("Save"):
        draft_param_data = st.session_state.repo[param_name].copy()
        draft_param_data["type"] = new_type
        draft_param_data["category"] = new_category
        draft_param_data["description"] = new_description
        
        if new_type == "array":
             constructed_nested = {}
             for nf in st.session_state[nested_state_key].values():
                 k = nf.get("key", "").strip()
                 if k:
                     item = {
                         "type": nf["type"],
                         "description": nf.get("description", "")
                     }
                     if "value" in nf:
                         val = nf.get("value")
                         if nf.get("type") == "number" and isinstance(val, str) and val.strip() != "":
                              try: val = float(val) if "." in val else int(val)
                              except: pass
                         item["value"] = val
                     elif "regex" in nf:
                         item["regex"] = nf.get("regex")
                         
                     constructed_nested[k] = item
             draft_param_data["nestedSchema"] = constructed_nested
             draft_param_data.pop("value", None)
             draft_param_data.pop("regex", None)
        else:
             if mode == "Fixed Value":
                 final_val = new_value
                 if new_type == "number" and isinstance(new_value, str) and new_value.strip() != "":
                     try: final_val = float(new_value) if "." in new_value else int(new_value)
                     except: pass
                 draft_param_data["value"] = final_val
                 draft_param_data.pop("regex", None)
             else:
                 draft_param_data["regex"] = new_regex
                 draft_param_data.pop("value", None)
                 
             if "nestedSchema" in draft_param_data:
                 del draft_param_data["nestedSchema"]
        
        repo = st.session_state.repo
        impacted_schemas = find_impacted_schemas(param_name, repo)
        
        full_schema_map = {}
        if impacted_schemas:
            full_names = [s if s.endswith(".json") else f"{s}.json" for s in impacted_schemas]
            
            with st.spinner(f"Preparing updates for {len(full_names)} schemas..."):
                # PARALLEL FETCH ALL IMPACTED 🚀
                original_contents = read_schemas_parallel(full_names)
                
                # PROCESS LOCALLY (INSTANT)
                new_props = construct_schema_definition(draft_param_data)
                for full_name, orig_data in original_contents.items():
                    if not orig_data: continue
                    
                    new_schema_data = copy.deepcopy(orig_data)
                    if param_name in new_schema_data:
                        new_schema_data[param_name] = new_props
                        
                    full_schema_map[full_name] = {
                        "original": orig_data,
                        "new": new_schema_data
                    }
        
        if full_schema_map:
            st.session_state.pending_confirmation = {
                "map": full_schema_map,
                "param_name": param_name,
                "draft_param_data": draft_param_data
            }
            if nested_state_key in st.session_state:
                del st.session_state[nested_state_key]
            st.rerun()
        else:
            st.session_state.repo[param_name] = draft_param_data
            writeRepoToJson(st.session_state.repo)
            st.toast(f"Parameter '{param_name}' updated.")
            
            # GRANULAR CACHE SYNC (No schemas updated, but health might be affected) 🧠
            sync_explorer_cache()
            
            if nested_state_key in st.session_state:
                del st.session_state[nested_state_key]
            st.rerun()



@st.dialog("Create parameter", width="large")
def myfn(id):
    newParamBuilder(id)