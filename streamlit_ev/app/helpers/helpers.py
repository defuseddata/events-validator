import streamlit as st
import json

from helpers.gcp import writeRepoToJson

# Toggle expanders
def toggle_expand_schema():
    st.session_state.expanded_schema = not st.session_state.expanded_schema

def toggle_expand_schema_builder():
    st.session_state.expanded_schema_builder = not st.session_state.expanded_schema_builder

# ID 
def next_id_for_schema():
    schema = st.session_state.get("schema", {})
    if not schema:
        return 2   # 0 = event_name, 1 = version

    ids = []
    for k in schema.keys():
        try:
            ids.append(int(k))
        except:
            pass
    return max(ids) + 1 if ids else 2

def add_field():
    schema = st.session_state.schema
    new_id = next_id_for_schema()
    schema[new_id] = {"key": "", "type": "", "value": "", "regex": "", "description": ""}
    st.session_state.schema = schema

def delete_field_and_rerun(field_id):
    schema = st.session_state.schema
    if field_id in schema:
        del schema[field_id]
    st.session_state.schema = schema
    st.rerun()

# Convert export → internal builder format
def convert_export_to_internal(export):
    internal = {}

    # event_name
    raw_event = export.get("event_name", {})
    internal[0] = {
        "key": "event_name",
        "type": "string",
        "value": raw_event.get("value", ""),
        "description": raw_event.get("description", "")
    }

    # version
    raw_version = export.get("version", {})
    internal[1] = {
        "key": "version",
        "type": "number",
        "value": raw_version.get("value", 0),
        "description": raw_version.get("description", "")
    }

    # custom fields
    next_id = 2
    for key, props in export.items():

        if key in ("event_name", "version"):
            continue

        if not isinstance(props, dict):
            props = {}

        field = {
            "key": key,
            "type": props.get("type", ""),
            "value": props.get("value", ""),
            "regex": props.get("regex", ""),
            "description": props.get("description", "") 
        }

        # array
        if props.get("type") == "array" and "nestedSchema" in props:
            nested = {}
            i = 0
            for nk, np in props["nestedSchema"].items():
                nested[i] = {
                    "key": nk,
                    "type": np.get("type", ""),
                    "value": np.get("value", ""),
                    "regex": np.get("regex", ""),
                    "description": np.get("description", "")
                }
                i += 1
            field["nestedSchema"] = nested

        internal[next_id] = field
        next_id += 1

    return internal


# Export builder → JSON
def export_schema():
    schema = st.session_state.schema
    export = {}

    # event_name
    ev = schema.get(0, {})
    export["event_name"] = {
        "type": "string",
        "value": ev.get("value", ""),
        "description": ev.get("description", "")  # <-- ADD DESCRIPTION
    }

    # version
    ver = schema.get(1, {})
    export["version"] = {
        "type": "number",
        "value": ver.get("value", 0),
        "description": ver.get("description", "")  # <-- ADD DESCRIPTION
    }

    # rest of fields
    for field_id in sorted(schema.keys()):
        if field_id < 2:
            continue

        field = schema[field_id]
        key = field["key"].strip()
        if not key:
            continue

        props = {
            "type": field.get("type", ""),
            "description": field.get("description", "")  # <-- ADD DESCRIPTION
        }

        if field["type"] != "array":
            val = field.get("value")
            if val not in ("", None, [], "Any"):
                if field["type"] == "number" and isinstance(val, str):
                    try: val = float(val) if "." in val else int(val)
                    except: pass
                props["value"] = val
            
            if field.get("regex") not in ("", None, []):
                props["regex"] = field["regex"]

        if field["type"] == "array" and "nestedSchema" in field:
            nested_export = {}

            for nested in field["nestedSchema"].values():
                nk = nested["key"].strip()
                if not nk:
                    continue

                np = {
                    "type": nested.get("type", ""),
                    "description": nested.get("description", "")
                }
                if nested.get("regex"):
                    np["regex"] = nested["regex"]
                
                # Check value before adding
                nv = nested.get("value")
                if nv not in ("", None, [], "Any"):
                    if nested.get("type") == "number" and isinstance(nv, str):
                        try: nv = float(nv) if "." in nv else int(nv)
                        except: pass
                    np["value"] = nv
                
                # Description
                np["description"] = nested.get("description", "")

                nested_export[nk] = np

            props["nestedSchema"] = nested_export

        export[key] = props

    return export


# RENDER FIELD ROW (NORMAL + NESTED)
def render_field_row(field_id, field, prefix, on_delete=None):
    cols = st.columns([3, 2, 3, 2, 1, 1])

    key_k = f"{prefix}_key_{field_id}"
    type_k = f"{prefix}_type_{field_id}"
    value_k = f"{prefix}_value_{field_id}"
    bool_k  = f"{prefix}_bool_{field_id}"
    regex_k = f"{prefix}_regex_{field_id}"
    desc_k  = f"{prefix}_desc_{field_id}"

    # FIELD NAME
    key_val = cols[0].text_input("Field", value=field.get("key", ""), key=key_k)

    # NESTED CANNOT USE ARRAY
    is_nested = prefix.startswith("schema_nested") or prefix.startswith("repo_nested")

    type_options = (
        ["string", "number", "boolean", "object"]
        if is_nested else
        ["string", "number", "boolean", "array", "object"]
    )

    current_type = field.get("type", "")
    if current_type not in type_options:
        current_type = type_options[0]

    type_val = cols[1].selectbox(
        "Type",
        type_options,
        index=type_options.index(current_type),
        key=type_k
    )

    # TYPE-SPECIFIC HANDLING
    if type_val == "array":
        cols[2].markdown("—")
        cols[3].markdown("—")
        value_val = ""
        regex_val = ""

    elif type_val == "number":
        try:
            initial_val = float(field.get("value", 0))
        except:
            initial_val = 0.0

        value_val = cols[2].number_input("Value (number)", value=initial_val, key=value_k)
        regex_val = ""
        cols[3].markdown("—")

    elif type_val == "boolean":
        raw = str(field.get("value", "")).lower()
        bool_default = (raw == "true")

        bool_val = cols[2].selectbox(
            "Value (boolean)",
            [True, False],
            index=0 if bool_default else 1,
            key=bool_k
        )

        value_val = "true" if bool_val else "false"
        regex_val = ""
        cols[3].markdown("—")

    else:
        value_val = cols[2].text_input("Value", value=field.get("value", ""), key=value_k)
        regex_val = cols[3].text_input("Regex", value=field.get("regex", ""), key=regex_k)

    if on_delete and cols[4].button("❌", key=f"{prefix}_delete_{field_id}"):
        on_delete(field_id)
        st.stop()

    cols[5].markdown(f"`{field_id}`")

    # DESCRIPTION FIELD
    desc_val = st.text_area(
        "Description",
        value=field.get("description", ""), 
        key=desc_k
    )

    return {
        "key": key_val,
        "type": type_val,
        "value": value_val,
        "regex": regex_val,
        "description": desc_val
    }


# RENDER ARRAY FIELD + NESTED FIELDS
def render_array_field(field_id, field, prefix, on_delete_field, update_schema):
    hcols = st.columns([3, 2, 4, 1])

    key_k = f"{prefix}_array_key_{field_id}"
    type_k = f"{prefix}_array_type_{field_id}"

    field["key"] = hcols[0].text_input("Array field", field.get("key", ""), key=key_k)
    hcols[1].text_input("Type", "array", disabled=True, key=type_k)

    exp_key = f"{prefix}_expanded_{field_id}"
    st.session_state.setdefault(exp_key, True)

    if hcols[2].button("🔼" if st.session_state[exp_key] else "🔽", key=f"{prefix}_collapse_{field_id}"):
        st.session_state[exp_key] = not st.session_state[exp_key]
        st.rerun()

    if hcols[3].button("❌", key=f"{prefix}_delete_array_{field_id}"):
        on_delete_field(field_id)
        st.rerun()

    if not st.session_state[exp_key]:
        return

    field.setdefault("nestedSchema", {})
    nested = field["nestedSchema"]

    for nid, nf in sorted(nested.items()):
        nid_label = f"{field_id}-{nid}"

        updated = render_field_row(
            nid_label,
            nf,
            prefix=f"{prefix}_nested",
            on_delete=lambda nid=nid: nested.pop(nid)
        )
        nf.update(updated)

    if st.button("➕ Add nested", key=f"{prefix}_add_nested_{field_id}"):
        next_nid = max(nested.keys(), default=-1) + 1
        nested[next_nid] = {"key": "", "type": "string", "value": "", "regex": "", "description": ""}
        st.rerun()

    update_schema(field_id, field)


# REPO → INTERNAL FORMAT
def convert_repo_param_to_internal(param_name: str, param_obj: dict):

    field = {}
    field["key"] = param_name
    field["type"] = param_obj.get("type", "")
    field["description"] = param_obj.get("description", "")

    if field["type"] != "array":
        field["value"] = param_obj.get("value", "")
        field["regex"] = param_obj.get("regex", "")
    else:
        field["value"] = ""
        field["regex"] = ""

    nested_src = param_obj.get("nestedSchema") or {}
    if isinstance(nested_src, dict) and nested_src:
        nested_internal = {}
        nid = 0
        for nested_key, nested_props in nested_src.items():
            nested_internal[nid] = {
                "key": nested_key,
                "type": nested_props.get("type", ""),
                "value": nested_props.get("value", ""),
                "regex": nested_props.get("regex", ""),
                "description": nested_props.get("description", "")
            }
            nid += 1
        field["nestedSchema"] = nested_internal

    return field

def add_schema_name_to_param_in_repo(param_name, schema_name):
    repo = st.session_state.get("repo", {})

    if param_name not in repo:
        return

    param = repo[param_name]

    if "usedInSchemas" not in param:
        param["usedInSchemas"] = []

    if schema_name not in param["usedInSchemas"]:
        param["usedInSchemas"].append(schema_name)


    writeRepoToJson(repo)



def update_repo_with_schema_usage(schema_name, schema_export_data):
    repo = st.session_state.get("repo", {})
    if not repo:
        return

    updated = False
    
    # Przejdź przez wszystkie pola w schemacie
    for field_name, field_props in schema_export_data.items():
        if field_name in ("event_name", "version"):
            continue

        # Jeśli nazwa pola jest też nazwą parametru w repo
        if field_name in repo:
            param = repo[field_name]
            if "usedInSchemas" not in param:
                param["usedInSchemas"] = []
            
            # Dodaj nazwę schematu jeśli nie ma
            if schema_name not in param["usedInSchemas"]:
                param["usedInSchemas"].append(schema_name)
                updated = True
    
    if updated:
        st.session_state.repo = repo
        writeRepoToJson(repo)
def readSchemaAndSetState(schema_data):
    internal = convert_export_to_internal(schema_data)
    st.session_state.schema = internal
    st.session_state.event_name = internal[0]["value"]
    st.session_state.schema_version = internal[1]["value"]
    st.session_state.toast_message = "Schema loaded into builder."
    st.session_state.page = "builder"


def render_param_compact(param: dict, indent: int = 2) -> str:
    if "nestedSchema" not in param:
        return json.dumps(param, ensure_ascii=False)

    lines = []
    indent_str = " " * indent

    # wszystko oprócz nestedSchema → inline
    inline_parts = {
        k: v for k, v in param.items() if k != "nestedSchema"
    }

    inline_json = json.dumps(inline_parts, ensure_ascii=False)
    inline_json = inline_json[:-1]  # usuń końcową }

    lines.append(f"{inline_json},")
    lines.append(f'{indent_str}"nestedSchema": {{')

    nested = param["nestedSchema"]
    nested_items = list(nested.items())

    for i, (k, v) in enumerate(nested_items):
        comma = "," if i < len(nested_items) - 1 else ""
        value_json = json.dumps(v, ensure_ascii=False)
        lines.append(f'{indent_str*2}"{k}": {value_json}{comma}')

    lines.append(f"{indent_str}}}")

    return "\n".join(lines)


def pretty_schema_inline(schema: dict) -> str:
    lines = ["{"]

    items = list(schema.items())
    for i, (key, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""

        if isinstance(value, dict) and "nestedSchema" in value:
            rendered = render_param_compact(value, indent=4)
            lines.append(f'  "{key}": {rendered}{comma}')
        else:
            inline = json.dumps(value, ensure_ascii=False)
            lines.append(f'  "{key}": {inline}{comma}')

    lines.append("}")
    return "\n".join(lines)
