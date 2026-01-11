import streamlit as st
import json
from helpers.helpers import (
    delete_field_and_rerun,
    export_schema,
    toggle_expand_schema,
    toggle_expand_schema_builder,
    next_id_for_schema,
    convert_repo_param_to_internal,
    add_schema_name_to_param_in_repo,
    pretty_schema_inline,
    update_repo_with_schema_usage
)
from helpers.gcp import uploadJson, readRepoFromJson


# RENDER READ-ONLY FIELD (NORMAL)

def render_schema_param(field_id, field):
    cols = st.columns([3, 2, 3, 1])

    # Compare with Repo default
    repo = st.session_state.get("repo", {})
    param_name = field.get("key", "")
    repo_default = repo.get(param_name, {}).get("value", "")
    
    # Robust comparison (0.0 vs 0)
    current_val = field.get("value", "")
    
    def values_match(v1, v2, p_type):
        if p_type == "number":
            try: return float(v1) == float(v2)
            except: return str(v1) == str(v2)
        return str(v1) == str(v2)

    is_overridden = not values_match(current_val, repo_default, field.get("type")) and param_name in repo

    label = f"Field {'⚖️' if is_overridden else ''}"
    cols[0].text_input(label, param_name, disabled=True, key=f"schema_key_{field_id}")

    cols[1].text_input(
        "Type",
        field.get("type", ""),
        disabled=True,
        key=f"schema_type_{field_id}",
    )

    if field.get("type") == "array":
        cols[2].markdown("—")
    elif field.get("type") == "boolean":
        opts = ["true", "false", "Any"]
        curr_idx = opts.index(str(current_val).lower()) if str(current_val).lower() in opts else 2
        new_val = cols[2].selectbox("Value", opts, index=curr_idx, key=f"schema_value_{field_id}")
        if new_val != str(current_val):
            field["value"] = new_val
            st.session_state.schema[field_id] = field
    elif field.get("type") == "number":
        # Use text_input to allow empty values for numbers
        new_val = cols[2].text_input("Value (number)", value=str(current_val) if current_val is not None else "", key=f"schema_value_{field_id}")
        if new_val != str(current_val):
            # Validate it's a number or empty
            if new_val.strip() == "":
                field["value"] = ""
            else:
                try: 
                    float(new_val)
                    field["value"] = new_val
                except ValueError:
                    st.error("Invalid number")
            st.session_state.schema[field_id] = field
    else:
        new_val = cols[2].text_input("Value", str(current_val), key=f"schema_value_{field_id}")
        if new_val != str(current_val):
            field["value"] = new_val
            st.session_state.schema[field_id] = field

    # Actions: Reset and Delete
    act_cols = cols[3].columns([1, 1])
    if is_overridden:
        if act_cols[0].button("🔄", key=f"schema_reset_{field_id}", help="Reset to Repo default"):
            field["value"] = repo_default
            st.session_state.schema[field_id] = field
            st.toast(f"Reset '{param_name}' to default.")
            st.rerun()
    
    if act_cols[1].button("❌", key=f"schema_delete_{field_id}"):
        delete_field_and_rerun(field_id)

    st.markdown("---")
# RENDER READ-ONLY ARRAY FIELD
def render_array_param(field_id, field):
    top = st.columns([5, 1, 1])
    with top[0]:
        st.markdown(f"### Array: `{field.get('key')}`")
        exp_key = f"array_expanded_{field_id}"
        st.session_state.setdefault(exp_key, True)
    # Toggle
    if top[1].button("🔼" if st.session_state[exp_key] else "🔽", key=f"toggle_arr_{field_id}"):
        st.session_state[exp_key] = not st.session_state[exp_key]
        st.rerun()

    # Delete
    if top[2].button("❌", key=f"delete_arr_{field_id}"):
        delete_field_and_rerun(field_id)
        st.stop()

    if not st.session_state[exp_key]:
        st.markdown("---")
        return

    st.markdown("#### Nested fields:")

    nested = field.get("nestedSchema", {}) or {}
    # Compare nested with Repo
    repo = st.session_state.get("repo", {})
    array_name = field.get("key", "")
    repo_nested = repo.get(array_name, {}).get("nestedSchema", {})

    for nid, nf in sorted(nested.items()):
        cols = st.columns([3, 2, 3, 1])
        n_key = nf.get("key", "")
        
        # Check override for nested
        r_nf = repo_nested.get(n_key, {})
        r_val = r_nf.get("value", "")
        is_n_overridden = str(nf.get("value", "")) != str(r_val) and n_key in repo_nested

        label = f"Key {'⚖️' if is_n_overridden else ''}"
        cols[0].text_input(label, n_key, disabled=True, key=f"arr_nested_key_{field_id}_{nid}")

        cols[1].text_input("Type", nf.get("type", ""), disabled=True, key=f"arr_nested_type_{field_id}_{nid}")
        
        # Type-specific nested values
        if nf.get("type") == "boolean":
            opts = ["true", "false", "Any"]
            c_val = str(nf.get("value", "")).lower()
            c_idx = opts.index(c_val) if c_val in opts else 2
            new_n_val = cols[2].selectbox("Value", opts, index=c_idx, key=f"arr_nested_value_{field_id}_{nid}")
        elif nf.get("type") == "number":
            new_n_val = cols[2].text_input("Value (number)", value=str(nf.get("value", "")) if nf.get("value") is not None else "", key=f"arr_nested_value_{field_id}_{nid}")
            if str(new_n_val) != str(nf.get("value", "")):
                if new_n_val.strip() == "":
                    nf["value"] = ""
                else:
                    try:
                        float(new_n_val)
                        nf["value"] = new_n_val
                    except ValueError:
                        st.error("Invalid number")
                st.session_state.schema[field_id]["nestedSchema"][nid] = nf

        if is_n_overridden:
            if cols[3].button("🔄", key=f"arr_nested_reset_{field_id}_{nid}", help="Reset to Repo default"):
                nf["value"] = r_val
                st.session_state.schema[field_id]["nestedSchema"][nid] = nf
                st.rerun()
    st.markdown("---")
# MAIN BUILDER UI
def render_builder():
    st.title("Schema Builder")

    st.session_state.setdefault("expanded_schema", True)
    st.session_state.setdefault("expanded_schema_builder", True)

    # Load repo
    try:
        repo = readRepoFromJson() or {}
    except Exception as e:
        repo = {}
        st.error(f"Failed to load parameters repo: {e}")

    st.session_state.repo = repo

    # Ensure schema exists
    st.session_state.setdefault("schema", {})
    schema = st.session_state.schema

    # EVENT NAME
    st.subheader("Event Name")
    st.caption("(required — used as schema filename)")

    if not st.session_state.get("event_name"):
        st.session_state.event_name = st.text_input(
            "Enter event_name",
            placeholder="purchase",
            key="event_name_input",
        )
    else:
        st.text_input(
            "Event name",
            st.session_state.event_name,
            disabled=True,
            key="event_name_show",
        )

    st.session_state.schema_version = st.number_input(
        "Schema Version",
        value=st.session_state.get("schema_version", 0),
        step=1,
        min_value=0,
        key="schema_version_input",
    )

    # Always set core fields
    schema[0] = {"key": "event_name", "type": "string", "value": st.session_state.event_name}
    schema[1] = {"key": "version", "type": "number", "value": st.session_state.schema_version}

    # PARAMETER PICKER
    st.markdown("---")
    st.subheader("Add Field From Parameters Repo")

    # Category filter
    categories = sorted({param.get("category", "Uncategorized") for param in repo.values()})
    selected_category = st.selectbox("Category", ["All"] + categories, key="category_filter")

    # Search filter
    query = st.text_input("Search parameter", key="search_param")

    # Remove already used keys
    used = {f.get("key") for f in schema.values()}
    available = [k for k in repo.keys() if k not in used]

    # Apply category filter
    if selected_category != "All":
        available = [k for k in available if repo[k].get("category") == selected_category]

    # Apply search filter
    if query:
        available = [k for k in available if query.lower() in k.lower()]

    if not available:
        st.info("No parameters available with current filters.")

    selected = st.selectbox("Choose parameter", available, key="choose_param")

    if st.button("➕ Add selected parameter", key="add_param_btn"):
        new_id = next_id_for_schema()
        internal = convert_repo_param_to_internal(selected, repo[selected])
        
        add_schema_name_to_param_in_repo(selected, st.session_state.event_name)
        
        schema[new_id] = internal

        st.session_state.schema = schema
        st.success(f"Added '{selected}' to schema.")
        st.rerun()

    # TWO COLUMN LAYOUT
    left, right = st.columns([2, 1])

    # LEFT — SCHEMA BUILDER
    with left:
        top = st.columns([4, 2])

        with top[0]:
            st.markdown("### Schema Fields")

        with top[1]:
            st.button(
                "🔼 Collapse fields" if st.session_state.expanded_schema_builder else "🔽 Expand fields",
                key="collapse_builder",
                on_click=toggle_expand_schema_builder,
            )

        if st.session_state.expanded_schema_builder:
            for field_id, field in sorted(schema.items()):
                if field_id in (0, 1):
                    continue

                if field.get("type") == "array":
                    render_array_param(field_id, field)
                else:
                    render_schema_param(field_id, field)

    # RIGHT — JSON PREVIEW
    with right:


        export = export_schema()
        
        compact = st.toggle("Compact schema view", value=True)

        if compact:
            st.code(pretty_schema_inline(export), language="json")
        else:
            st.json(export)


        def handle_gcp_upload(data, filename, event_name):
            uploadJson(data, filename)
            if st.session_state.get("upload_status"):
                update_repo_with_schema_usage(event_name, data)

        if st.session_state.event_name.strip():
            st.button(
                "Send to GCP",
                on_click=handle_gcp_upload,
                args=(export, f"{st.session_state.event_name}.json", st.session_state.event_name),
                type="primary",
                key="send_gcp_btn",
            )
        else:
            st.error("Event name is required")

    # Toasts
    if st.session_state.get("toast_message"):
        st.toast(st.session_state.toast_message)
        st.session_state.toast_message = None
