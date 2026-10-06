import time
import streamlit as st
import json
import os
import copy
from helpers.storage import (
    read_repo,
    write_repo,
    read_schemas_parallel,
    is_github_mode,
    get_current_branch,
    clear_cache,
)
from helpers.components import render_branch_selector, render_storage_status
from helpers.helpers import render_field_row, pretty_schema_inline
from helpers.updater import (
    find_impacted_schemas,
    apply_updates,
    render_diff_ui,
    construct_schema_definition,
    update_schema_full,
    check_schema_health,
    preserve_schema_customization
)
from dotenv import load_dotenv

load_dotenv()

repo_file_name = os.getenv("REPO_JSON_FILE") or "repo.json"
typeOptions = ["string", "number", "boolean", "array"]

_MARKDOWN_SPECIAL_CHARS = r"\`*_{}[]()#+-.!|>~"

def md_escape(text):
    """Escapes Markdown special characters so free-text repo fields (typed by
    any user with repo-edit access) render as literal text in st.markdown
    instead of being interpreted as headings, links, or colored spans."""
    text = str(text)
    for ch in _MARKDOWN_SPECIAL_CHARS:
        text = text.replace(ch, "\\" + ch)
    return text

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
        repo = read_repo() or {}
        st.session_state.repo = clean_repo_types(repo)

# available_categories = sorted({param.get("category", "Uncategorized") for param in st.session_state.repo.values()})
def get_available_categories():
    return sorted({
        param.get("category", "Uncategorized")
        for param in st.session_state.get("repo", {}).values()
        if param.get("category")
    })


_NEW_CATEGORY_SENTINEL = "__add_new_category__"
_RESERVED_CATEGORY_NAMES = {"none", "uncategorized", "all categories", ""}


def render_category_picker(container, current_category, key_prefix):
    """Selectbox with a '— No category —' option and a '+ Add new category…'
    option that reveals a text input, instead of typing new options inline
    (which was confusing — see .dev/handoffs)."""
    existing = get_available_categories()
    options = [""] + existing
    if current_category and current_category not in options:
        options = options + [current_category]
    options = options + [_NEW_CATEGORY_SENTINEL]

    def _fmt(c):
        if c == "":
            return "— No category —"
        if c == _NEW_CATEGORY_SENTINEL:
            return "+ Add new category…"
        return c

    idx = options.index(current_category) if current_category in options else 0
    choice = container.selectbox(
        "Category", options, index=idx, key=f"{key_prefix}_select", format_func=_fmt,
    )
    if choice == _NEW_CATEGORY_SENTINEL:
        typed = container.text_input(
            "New category name", key=f"{key_prefix}_new_name", placeholder="e.g. Marketing",
        ).strip()
        if typed and typed.lower() in _RESERVED_CATEGORY_NAMES:
            container.error(f"'{typed}' is a reserved name and can't be used as a category. Keeping the previous category.")
            return current_category
        return typed
    return choice


# RENDER REPO

def render_repo():
    ensure_repo_loaded()
    if "show_new_param_builder" not in st.session_state:
        st.session_state.show_new_param_builder = False

    # Branch selector and storage info
    if is_github_mode():
        col_branch, col_status = st.columns([2, 3])
        with col_branch:
            render_branch_selector(key="repo_branch")
        with col_status:
            render_storage_status()

    col = st.columns([1, 1])
    with col[0]:
        st.title("Parameters Repository")
        if st.button("Add new parameter", type="primary"):
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
        col_category, col_search = st.columns([2, 3], vertical_alignment="center")
        with col_category:
            has_uncategorized = any(not param.get("category") for param in repo.values())
            category_filter = st.selectbox(
                "Filter by category",
                ["All Categories"] + ([""] if has_uncategorized else []) + get_available_categories(),
                key="repo_category_filter",
                label_visibility="collapsed",
                format_func=lambda c: "— No category —" if c == "" else c,
            )
        with col_search:
            query = st.text_input(
                "Search parameter",
                key="repo_search",
                label_visibility="collapsed",
                placeholder="Search parameter",
            )

        filtered_repo = list(repo.items())
        if query:
            filtered_repo = [(name, param) for name, param in filtered_repo if query.lower() in name.lower()]
        if category_filter != "All Categories":
            filtered_repo = [
                (name, param) for name, param in filtered_repo
                if (param.get("category") or "") == category_filter
            ]
        if not filtered_repo:
            st.info("No parameters match the current filters.")

        for name, param in filtered_repo:
            category = param.get("category") or "— No category —"
            param_type = param.get("type", "Undefined")

            exp_label = (
                f"{name}   |   "
                f"category: {category}   |   "
                f"type: {param_type}"
            )

            with st.expander(exp_label, expanded=False):
                cols = st.columns([2,2])

                with cols[0]:
                    st.markdown(
                        f"**Type:** {md_escape(param.get('type', ''))}  \n"
                        f"**Default Value:** {md_escape(param.get('value', ''))}  \n"
                        f"**Category:** {md_escape(param.get('category', ''))}  \n"
                        f"**Description:** {md_escape(param.get('description', ''))}  \n"
                        f"**Used In:** {md_escape(json.dumps(param.get('usedInSchemas', '')))}"
                    )
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
                if isinstance(key, str) and (key.startswith("repo_") or key.startswith("custom_cat_")):
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
    commit_msg = "Update parameter repository"
    success, message = write_repo(repoData, commit_message=commit_msg)
    if not success:
        st.error(f"Failed to save repository: {message}")


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

def add_bulk_param():
    if "bulk_params" not in st.session_state:
        st.session_state.bulk_params = {}
    
    new_id = max(st.session_state.bulk_params.keys(), default=-1) + 1
    st.session_state.bulk_params[new_id] = {
        "name": "",
        "type": "string",
        "category": "",
        "has_default": False,
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
            cols = st.columns([3, 2, 2, 4, 1])

            p_data["name"] = cols[0].text_input("Name", p_data["name"], key=f"bp_name_{pid}")
            prev_p_type = p_data["type"]
            p_data["type"] = cols[1].selectbox("Type", typeOptions, key=f"bp_type_{pid}", index=typeOptions.index(p_data["type"]) if p_data["type"] in typeOptions else 0)
            if p_data["type"] != prev_p_type:
                # Drop the old value/regex — otherwise a leftover boolean
                # value like "Any" silently becomes the new string default.
                p_data["value"] = "Any" if p_data["type"] == "boolean" else ""
                p_data["regex"] = ""

            p_data["category"] = render_category_picker(cols[2], p_data["category"], f"bp_cat_{pid}")

            p_data["description"] = cols[3].text_area("Description", p_data["description"], key=f"bp_desc_{pid}", height=68)

            if len(st.session_state.bulk_params) > 1:
                cols[4].button("X", key=f"bp_del_{pid}", on_click=delete_bulk_param, args=(pid,))

            if p_data["type"] != "array":
                default_cols = st.columns([2, 2, 4])
                has_default = default_cols[0].radio(
                    "Default value?",
                    ["No default value", "Set a default value"],
                    index=1 if p_data.get("has_default") else 0,
                    key=f"bp_has_default_{pid}",
                ) == "Set a default value"
                p_data["has_default"] = has_default

                if has_default:
                    if p_data["type"] == "boolean":
                        p_data["mode"] = "Value"
                    else:
                        mode_choice = default_cols[1].radio(
                            "Validation Type",
                            ["Fixed Value", "Regex Pattern"],
                            index=0 if p_data["mode"] == "Value" else 1,
                            key=f"bp_mode_{pid}",
                        )
                        p_data["mode"] = "Value" if mode_choice == "Fixed Value" else "Regex"

                    if p_data["mode"] == "Value":
                        if p_data["type"] == "boolean":
                             p_data["value"] = default_cols[1].selectbox(
                                 "Default Value", ["true", "false", "Any"], key=f"bp_val_{pid}_{p_data['type']}",
                                 index=["true", "false", "Any"].index(str(p_data["value"]).lower()) if str(p_data["value"]).lower() in ["true", "false", "Any"] else 2,
                                 help="Choose 'Any' if this parameter has no default value.",
                             )
                        elif p_data["type"] == "number":
                             v = p_data.get("value")
                             num_v = str(v) if v is not None and str(v).strip() != "" else ""
                             p_data["value"] = default_cols[2].text_input(
                                 "Default Value", value=num_v, placeholder="empty", key=f"bp_val_{pid}_{p_data['type']}",
                                 help="Leave empty if this parameter has no default value.",
                             )
                             if isinstance(p_data["value"], str) and p_data["value"].strip() != "":
                                 try: float(p_data["value"])
                                 except: default_cols[2].error("Invalid number", icon="⚠️")
                        else:
                             p_data["value"] = default_cols[2].text_input(
                                 "Default Value", p_data["value"], key=f"bp_val_{pid}_{p_data['type']}",
                                 placeholder="empty",
                                 help="Leave empty if this parameter has no default value.",
                             )
                    else:
                        p_data["regex"] = default_cols[2].text_input(
                            "Regex", p_data["regex"], key=f"bp_regex_{pid}",
                            help="Standard JavaScript regex pattern — no leading/trailing `/`. "
                                 "Example: `^[A-Z]{2}\\d{4}$` matches two uppercase letters followed by 4 digits.",
                        )
                else:
                    p_data["mode"] = "Value"
                    p_data["value"] = "Any" if p_data["type"] == "boolean" else ""
                    default_cols[2].caption("No default value or pattern will be set for this parameter.")

            # Nested fields for Array
            if p_data["type"] == "array":
                with st.expander(f"Nested fields for '{p_data['name']}'", expanded=True):
                    nested_items = sorted(p_data["nested"].items())
                    for nid, nf in nested_items:
                        r = st.columns([3, 2, 2, 2, 1])
                        nf["key"] = r[0].text_input("Key", nf["key"], key=f"bp_n_key_{pid}_{nid}")

                        prev_nf_type = nf.get("type", "string")
                        nf["type"] = r[1].selectbox("Type", ["string", "number", "boolean"], key=f"bp_n_type_{pid}_{nid}", index=["string", "number", "boolean"].index(prev_nf_type) if prev_nf_type in ("string", "number", "boolean") else 0)
                        if nf["type"] != prev_nf_type:
                            nf["value"] = "Any" if nf["type"] == "boolean" else ""
                            nf.pop("regex", None)

                        if nf["type"] == "boolean":
                            nf["mode"] = "Value"
                        else:
                            nf["mode"] = r[2].selectbox("Validation", ["Value", "Regex"], key=f"bp_n_mode_{pid}_{nid}_{nf['type']}", index=0 if nf.get("mode", "Value") == "Value" else 1)

                        if nf["mode"] == "Value":
                            if nf["type"] == "boolean":
                                nf["value"] = r[3].selectbox("Value", ["true", "false", "Any"], key=f"bp_n_val_{pid}_{nid}_{nf['type']}", index=["true", "false", "Any"].index(str(nf.get("value", "Any")).lower()) if str(nf.get("value", "Any")).lower() in ["true", "false", "Any"] else 2)
                            elif nf["type"] == "number":
                                v = nf.get("value")
                                num_v = str(v) if v is not None and str(v).strip() != "" else ""
                                nf["value"] = r[3].text_input("Value", value=num_v, placeholder="empty", key=f"bp_n_val_{pid}_{nid}_{nf['type']}")
                                if isinstance(nf["value"], str) and nf["value"].strip() != "":
                                    try: float(nf["value"])
                                    except: r[3].error("Invalid number", icon="⚠️")
                            else:
                                nf["value"] = r[3].text_input("Value", nf.get("value", ""), placeholder="empty", key=f"bp_n_val_{pid}_{nid}_{nf['type']}")
                        else:
                            nf["regex"] = r[3].text_input("Regex", nf.get("regex", ""), key=f"bp_n_regex_{pid}_{nid}")

                        r[4].button("X", key=f"bp_n_del_{pid}_{nid}", on_click=delete_nested_bulk, args=(pid, nid))
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

            # validate numbers
            ok_to_save = True
            if p_data["type"] == "number" and p_data["mode"] == "Value":
                val = p_data.get("value", "")
                if isinstance(val, str) and val.strip() != "":
                    try: float(val)
                    except:
                        errors.append(f"Parameter '{name}' has an invalid number.")
                        ok_to_save = False
            if p_data.get("type") == "array":
                for nf in p_data.get("nested", {}).values():
                    if nf.get("type") == "number" and nf.get("mode", "Value") == "Value":
                        val = nf.get("value", "")
                        if isinstance(val, str) and val.strip() != "":
                            try: float(val)
                            except:
                                errors.append(f"Nested field '{nf.get('key')}' in '{name}' has an invalid number.")
                                ok_to_save = False
            if not ok_to_save:
                continue

            new_param = {
                "type": p_data["type"],
                "category": p_data["category"],
                "description": p_data["description"]
            }

            if p_data.get("type") == "array":
                constructed_nested = {}
                for nf in p_data.get("nested", {}).values():
                    k = nf.get("key", "").strip()
                    if k:
                        item = {
                            "type": nf.get("type", "string"),
                            "description": nf.get("description", "")
                        }
                        if nf.get("mode", "Value") == "Value":
                             val = nf.get("value")
                             if nf.get("type", "string") == "number" and isinstance(val, str) and val.strip() != "":
                                  try: val = float(val) if "." in val else int(val)
                                  except: pass
                             if val is not None and str(val).strip() != "":
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
                    if val is not None and str(val).strip() != "":
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
            write_repo(repo, commit_message="Add new parameters")
            st.success(f"Successfully added {saved_count} parameters.")
            # Clear bulk params
            st.session_state.bulk_params = {}
            time.sleep(2)
            st.rerun()
        elif not errors:
             st.warning("No valid parameters to save.")


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

    search_query = st.text_input("Search schemas", key="confirm_update_search", placeholder="Filter by schema name…")
    filtered_schema_map = {
        name: data for name, data in full_schema_map.items()
        if search_query.lower() in name.lower()
    } if search_query else full_schema_map
    if search_query and not filtered_schema_map:
        st.caption(f"No schemas match '{search_query}'.")

    # We need keys for checkboxes.
    for schema_name, data in filtered_schema_map.items():
        # Checkbox for each schema
        # Use a container to group checkbox and expander
        c1, c2 = st.columns([0.1, 0.9])
        with c1:
            # Seed initial state via setdefault only — toggle_all() sets
            # these directly via the Session State API, so the widget must
            # not also receive a `value=` default (Streamlit warns/conflicts
            # when both happen for the same key).
            st.session_state.setdefault(f"chk_{schema_name}", st.session_state.get("master_toggle_schemas", True))
            st.checkbox("Select Schema", key=f"chk_{schema_name}", label_visibility="collapsed")
        with c2:
            with st.expander(f"Review: {schema_name}", expanded=False):
                render_diff_ui(data["original"], data["new"], param_name)
    
    # Read selection from the full map, not just what the search filter
    # rendered this pass — otherwise selecting a schema then filtering it
    # out of view would silently drop it before Confirm & Update.
    selected_schemas = [
        name for name in full_schema_map.keys()
        if st.session_state.get(f"chk_{name}", st.session_state.get("master_toggle_schemas", True))
    ]

    # ---------------------------------------------------------
    # CLEANUP HELPER
    def cleanup_confirmation():
        if "pending_confirmation" in st.session_state:
            del st.session_state.pending_confirmation
        if "master_toggle_schemas" in st.session_state:
            del st.session_state.master_toggle_schemas
        if "confirm_update_search" in st.session_state:
            del st.session_state.confirm_update_search
        for k in list(st.session_state.keys()):
            if isinstance(k, str) and k.startswith("chk_"):
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
                write_repo(st.session_state.repo, commit_message="Update parameter")
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
        current_has_default = bool(current_regex) or (
            str(current_value).strip() != "" and not (new_type == "boolean" and str(current_value).lower() == "any")
        )
        set_default = st.radio(
            "Does this parameter have a default value?",
            ["No default value", "Set a default value"],
            index=1 if current_has_default else 0,
            horizontal=True,
            key=f"edit-{param_name}-has-default",
        ) == "Set a default value"

        if set_default:
            if new_type == "boolean":
                mode = "Fixed Value"
            else:
                mode = st.radio("Validation Type", ["Fixed Value", "Regex Pattern"],
                                index=1 if current_regex else 0, horizontal=True,
                                key=f"edit-{param_name}-mode")

            if mode == "Fixed Value":
                if new_type == "boolean":
                    opts = ["true", "false", "Any"]
                    cv_str = str(current_value).lower()
                    curr_val_idx = opts.index(cv_str) if cv_str in opts else 2
                    new_value = st.selectbox(
                        "Default Value", opts, index=curr_val_idx, key=f"edit_{param_name}-value-bool",
                        help="Choose 'Any' if this parameter has no default value.",
                    )
                elif new_type == "number":
                    num_k = f"edit_{param_name}-value-num"
                    if num_k in st.session_state:
                        curr_num = st.session_state[num_k]
                    else:
                        curr_num = str(current_value) if current_value is not None and str(current_value).strip() != "" else ""
                    new_value = st.text_input(
                        "Default Value", value=curr_num, placeholder="empty", key=num_k,
                        help="Leave empty if this parameter has no default value.",
                    )
                    if isinstance(new_value, str) and new_value.strip() != "":
                        try: float(new_value)
                        except: st.error("Invalid number", icon="⚠️")
                else:
                    text_k = f"edit_{param_name}-value"
                    if text_k in st.session_state:
                        curr_text = st.session_state[text_k]
                    else:
                        curr_text = current_value if current_value else ""
                    new_value = st.text_input(
                        "Default Value",
                        value=curr_text,
                        placeholder="empty",
                        help="Leave empty if this parameter has no default value.",
                        key=text_k
                    )
            else:
                new_regex = st.text_input(
                    "Regex Pattern", value=current_regex, key=f"edit_{param_name}-regex",
                    help="Standard JavaScript regex pattern — no leading/trailing `/`. "
                         "Example: `^[A-Z]{2}\\d{4}$` matches two uppercase letters followed by 4 digits.",
                )
        else:
            mode = "Fixed Value"
            new_value = "Any" if new_type == "boolean" else ""
            st.caption("No default value or pattern will be set for this parameter.")
    else:
        st.caption("Nested fields for Array:")
        edit_nested = st.session_state[nested_state_key]
        
        for nid, nf in edit_nested.items():
            r = st.columns([3, 2, 2, 2, 1])
            nf["key"] = r[0].text_input("Key", nf.get("key", ""), key=f"ed_nk_{param_name}_{nid}")

            prev_n_type = nf.get("type", "string")
            nf["type"] = r[1].selectbox(
                "Type", ["string", "number", "boolean"],
                index=["string", "number", "boolean"].index(prev_n_type) if prev_n_type in ("string", "number", "boolean") else 0,
                key=f"ed_nt_{param_name}_{nid}",
            )
            # Switching type must drop the old value/regex — otherwise a
            # leftover boolean value like "Any" silently becomes the string
            # default (no error, since any text is a "valid" string) instead
            # of being reset. Type-scoped widget keys below back this up by
            # never reusing another type's committed widget state.
            if nf["type"] != prev_n_type:
                nf["value"] = "Any" if nf["type"] == "boolean" else ""
                nf.pop("regex", None)

            if nf["type"] == "boolean":
                nest_mode = "Value"
            else:
                nest_mode = r[2].selectbox(
                    "Validation", ["Value", "Regex"],
                    key=f"ed_mode_{param_name}_{nid}_{nf['type']}",
                    index=1 if nf.get("regex") else 0,
                )
            if nest_mode == "Value":
                if nf["type"] == "boolean":
                     opts = ["true", "false", "Any"]
                     cval = str(nf.get("value", "Any")).lower()
                     cidx = opts.index(cval) if cval in opts else 2
                     nf["value"] = r[3].selectbox("Value", opts, index=cidx, key=f"ed_nv_{param_name}_{nid}_{nf['type']}")
                elif nf["type"] == "number":
                     v = nf.get("value")
                     num_v = str(v) if v is not None and str(v).strip() != "" else ""
                     nf["value"] = r[3].text_input("Value", value=num_v, placeholder="empty", key=f"ed_nv_{param_name}_{nid}_{nf['type']}")
                     if isinstance(nf["value"], str) and nf["value"].strip() != "":
                         try: float(nf["value"])
                         except: r[3].error("Invalid number", icon="⚠️")
                else:
                     nf["value"] = r[3].text_input("Value", nf.get("value", ""), placeholder="empty", key=f"ed_nv_{param_name}_{nid}_{nf['type']}")
                nf.pop("regex", None)
            else:
                nf["regex"] = r[3].text_input("Regex Pattern", nf.get("regex", ""), key=f"ed_nr_{param_name}_{nid}")
                nf.pop("value", None)
                 
            r[4].button("X", key=f"ed_del_{param_name}_{nid}", on_click=delete_nested_edit, args=(param_name, nid))
            nf["description"] = st.text_area("Description", nf.get("description", ""), key=f"ed_nd_{param_name}_{nid}", height=68)
            st.markdown("---")
            
        st.button("➕ Add nested key", key=f"ed_add_{param_name}", on_click=add_nested_edit, args=(param_name,))

    new_category = render_category_picker(st, current_category, f"edit-{param_name}-category")
    new_description = st.text_area(
        "Description",
        key=f"edit-{param_name}-description",
        value=current_description,
        placeholder="Describe what this parameter means, how it's used, constraints, notes…"
    )
    
    # TYPE CHANGE NOTICE — the value/regex widgets above already use
    # type-scoped keys (e.g. "...-value-bool" / "...-value-num"), so they
    # already show a fresh, type-appropriate default the moment the type
    # changes. This used to also overwrite new_value with a hardcoded
    # placeholder here, which clobbered whatever the user had just typed
    # into that same-render widget — removed.
    if new_type != current_type:
        st.info(f"💡 Type changed from `{current_type}` to `{new_type}`.")

    if st.button("Save"):
        if new_type == "number" and mode == "Fixed Value":
             if isinstance(new_value, str) and new_value.strip() != "":
                 try: float(new_value)
                 except: 
                     st.error("Invalid number format for value!")
                     st.stop()
        if new_type == "array":
             for nf in st.session_state[nested_state_key].values():
                 if nf.get("type") == "number" and nf.get("mode", "Value") == "Value":
                     nv = nf.get("value", "")
                     if isinstance(nv, str) and nv.strip() != "":
                         try: float(nv)
                         except:
                             st.error(f"Invalid number format for nested key {nf.get('key', '')}")
                             st.stop()

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
                         if val is not None and str(val).strip() != "":
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
                 if final_val is not None and str(final_val).strip() != "":
                     draft_param_data["value"] = final_val
                 else:
                     draft_param_data.pop("value", None)
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
                repo_new_props = construct_schema_definition(draft_param_data)
                for full_name, orig_data in original_contents.items():
                    if not orig_data: continue

                    new_schema_data = copy.deepcopy(orig_data)
                    if param_name in new_schema_data:
                        # Repo wins on value/regex/Contains; the schema's own
                        # Optional/Conditional rules are always kept, since
                        # the repo has no concept of them at all.
                        new_schema_data[param_name] = preserve_schema_customization(
                            orig_data.get(param_name, {}), repo_new_props
                        )

                    # Skip schemas the edit wouldn't actually change — e.g.
                    # editing only the parameter's category, which never
                    # appears in the exported schema JSON at all. Without
                    # this, every impacted schema shows up in Confirm Schema
                    # Updates even when its "new" JSON is byte-for-byte
                    # identical to "original".
                    if new_schema_data.get(param_name) == orig_data.get(param_name):
                        continue

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
            write_repo(st.session_state.repo, commit_message="Update parameter")
            st.toast(f"Parameter '{param_name}' updated.")
            
            # GRANULAR CACHE SYNC (No schemas updated, but health might be affected) 🧠
            sync_explorer_cache()
            
            if nested_state_key in st.session_state:
                del st.session_state[nested_state_key]
            st.rerun()



@st.dialog("Create parameter", width="large")
def myfn(id):
    newParamBuilder(id)