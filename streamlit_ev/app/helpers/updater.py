import streamlit as st
import json
import copy
from helpers.gcp import readSchemaToJson, uploadJson
from helpers.helpers import convert_repo_param_to_internal, export_schema
def construct_schema_definition(param_data: dict) -> dict:
    """
    Constructs the standard parameter definition dictionary for the export schema
    based on the repository parameter data.
    """
    raw_value = param_data.get("value")
    
    props = {
        "type": param_data.get("type", ""),
        "description": param_data.get("description", ""),
    }
    
    # Validated Value Logic (casts strings to correct types if needed)
    final_value = None
    if raw_value is not None:
         # Filter out basics
         if isinstance(raw_value, str):
             if raw_value.strip() == "" or raw_value == "Any":
                 pass
             else:
                 # It has content. Try to cast based on type.
                 if param_data.get("type") == "number":
                     try:
                         final_value = float(raw_value) if "." in raw_value else int(raw_value)
                     except:
                         final_value = raw_value # Fallback
                 elif param_data.get("type") == "boolean":
                      if raw_value.lower() == "true": final_value = True
                      elif raw_value.lower() == "false": final_value = False
                      else: final_value = None # Should not happen if "Any" caught above
                 else:
                     final_value = raw_value
         else:
             final_value = raw_value

    if final_value is not None:
        props["value"] = final_value
    
    # Handling Arrays 
    if param_data.get("type") == "array" and "nestedSchema" in param_data:
        nested_export = {}
        for nk, np in param_data["nestedSchema"].items():
             n_props = {
                 "type": np.get("type", ""),
                 "description": np.get("description", ""),
             }
             if np.get("regex"):
                 n_props["regex"] = np["regex"]
             
             # Filter nested value
             n_raw_val = np.get("value")
             n_final_val = None
             
             if n_raw_val is not None:
                 if isinstance(n_raw_val, str):
                     if n_raw_val.strip() == "" or n_raw_val == "Any":
                         pass
                     else:
                         if np.get("type") == "number":
                             try:
                                 n_final_val = float(n_raw_val) if "." in n_raw_val else int(n_raw_val)
                             except:
                                 n_final_val = n_raw_val
                         elif np.get("type") == "boolean":
                              if n_raw_val.lower() == "true": n_final_val = True
                              elif n_raw_val.lower() == "false": n_final_val = False
                         else:
                             n_final_val = n_raw_val
                 else:
                     n_final_val = n_raw_val

             if n_final_val is not None:
                 n_props["value"] = n_final_val

             nested_export[nk] = n_props
             
        props["nestedSchema"] = nested_export
        
    return props

def find_impacted_schemas(param_name: str, repo_data: dict) -> list:
    """
    Returns a list of schema names (e.g., "event_v1.json") that use the given param.
    """
    if param_name not in repo_data:
        return []
    
    param = repo_data[param_name]
    return param.get("usedInSchemas", [])

def rebuild_schema_dry_run(schema_name: str, param_name: str, new_param_data: dict):
    """
    Downloads the schema, updates the specific parameter definition,
    and returns a tuple (original_schema_dict, new_schema_dict).
    The 'new_schema_dict' is in the EXPORT format (ready for JSON upload).
    """
    try:
        # 1. Download existing schema (Export format)
        original_export_schema = readSchemaToJson(schema_name)
    except Exception as e:
        pass
        return {}, {}

    if not original_export_schema:
        return {}, {}

    # Deep copy to create the new version
    new_export_schema = copy.deepcopy(original_export_schema)

    # 2. Find where the parameter is used in the schema
    # We assume key matches param_name for V1 auto-update
    
    # props mapping
    new_props = construct_schema_definition(new_param_data)

    # Apply to Schema
    if param_name in new_export_schema:
            # Clean replacement of properties to ensure no ghost keys (like nestedSchema) remain
            # But we want to preserve 'value' if it exists in the SCHEMA and aligns with new type
            # (unless we strictly want repo enforcement, which we decided earlier).
            
            # Actually, we decided earlier: "Update" implies enforcing repo state.
            # So if we simply ASSIGN new_props to the key, we wipe everything else.
            # EXCEPT: The schema structure might have other keys? 
            # Usually export schema is simple: { param: { type: ..., desc: ... }, ... }
            # So FULL REPLACEMENT is safer and cleaner than .update()
            
            new_export_schema[param_name] = new_props
            
            # However, if we wanted to respect "compatible value preservation" logic from before?
            # User said: "why editing parameter type string and editing it's value does not affect schema"
            # So user WANTS repo value to win.
            # So strict replacement is exactly what is needed.
            pass
        
    return original_export_schema, new_export_schema

def apply_updates(schema_map: dict):
    """
    schema_map: { "schema_name": new_json_data }
    """
    success_count = 0
    errors = []
    
    for schema_name, new_data in schema_map.items():
        try:
            uploadJson(new_data, schema_name, silent=True)
            success_count += 1
        except Exception as e:
            errors.append(f"{schema_name}: {str(e)}")
            
    return success_count, errors

def render_diff_ui(original: dict, new: dict, param_focus: str):
    """
    Renders a side-by-side diff of the specific parameter within the schema.
    """
    
    # Extract just the relevant part for clearer diff
    orig_part = original.get(param_focus, {})
    new_part = new.get(param_focus, {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Current Schema (GCP)")
        st.json(orig_part)
    with col2:
        st.caption("New Schema (Preview)")
        st.json(new_part)

def check_schema_health(schema_data: dict, repo_data: dict) -> list:
    """
    Compares schema parameters against the repository.
    Returns a list of parameter names that differ from the repo definition.
    """
    outdated = []
    
    for param_name, schema_param in schema_data.items():
        if param_name in ("event_name", "version"):
            continue
            
        if param_name not in repo_data:
            continue
            
        repo_param = repo_data[param_name]
        
        # Construct what it SHOULD be
        expected_props = construct_schema_definition(repo_param)
        
        # Compare Type
        if schema_param.get("type") != expected_props.get("type"):
            outdated.append(param_name)
            continue
            
        # Compare Description
        if schema_param.get("description", "") != expected_props.get("description", ""):
            outdated.append(param_name)
            continue

        # Compare Regex
        if "regex" in expected_props:
             if schema_param.get("regex") != expected_props["regex"]:
                 outdated.append(param_name)
                 continue
            
        # Compare Nested Schema (for Arrays)
        if expected_props.get("type") == "array" and "nestedSchema" in expected_props:
            current_nested = schema_param.get("nestedSchema", {})
            expected_nested = expected_props["nestedSchema"]
            
            # Deep normalization and comparison
            is_mismatch = False
            if len(current_nested) != len(expected_nested):
                is_mismatch = True
            else:
                for nk, ev in expected_nested.items():
                    if nk not in current_nested:
                        is_mismatch = True
                        break
                    
                    cv = current_nested[nk]
                    # Compare keys strictly to allow cleaning up empty ghost keys (like regex: "")
                    for key in ("type", "value", "regex", "description"):
                        val_c = cv.get(key)
                        val_e = ev.get(key)
                        
                        # Normalize for functional equality
                        norm_c = val_c if val_c not in ("Any", "") else None
                        norm_e = val_e if val_e not in ("Any", "") else None

                        # Number normalization
                        if key == "value" and cv.get("type") == "number":
                            try:
                                if norm_c is not None: norm_c = float(norm_c)
                                if norm_e is not None: norm_e = float(norm_e)
                            except: pass
                        
                        if norm_c != norm_e:
                            is_mismatch = True
                            break
                        
                        # Detect if key exists in bucket but shouldn't (Ghost Key cleanup)
                        if val_c is not None and val_e is None:
                            is_mismatch = True
                            break
                    if is_mismatch: break
            
            if is_mismatch:
                 outdated.append(param_name)
                 continue

        # Compare Value
        s_val = schema_param.get("value")
        e_val = expected_props.get("value")

        # Normalize "Any" or empty string to None
        if s_val in ("Any", "", None): s_val = None
        if e_val in ("Any", "", None): e_val = None

        # Normalize number types for comparison
        if schema_param.get("type") == "number":
             try:
                 if s_val is not None: s_val = float(s_val)
                 if e_val is not None: e_val = float(e_val)
             except: pass

        if s_val != e_val:
             outdated.append(param_name)
             continue

    return outdated

def update_schema_full(schema_name: str, repo_data: dict):
    """
    Iterates through all parameters in the schema.
    If a parameter exists in the repo, it updates the schema definition to match the repo.
    Uploads the result.
    """
    try:
        current_schema = readSchemaToJson(schema_name)
        if not current_schema:
            return False, ["Schema not found"]
            
        new_schema = copy.deepcopy(current_schema)
        updates_made = False
        
        for param_name in list(new_schema.keys()):
            if param_name in ("event_name", "version"):
                continue
            
            if param_name in repo_data:
                # Use shared logic
                repo_param = repo_data[param_name]
                new_props = construct_schema_definition(repo_param)
                
                # Use clean replacement to avoid ghost keys (e.g. old "value" when it's now "Any")
                new_schema[param_name] = new_props
                
                updates_made = True

        if updates_made:
            uploadJson(new_schema, schema_name, silent=True)
            return True, []
        else:
            return False, ["No updates needed"]

    except Exception as e:
        return False, [str(e)]
