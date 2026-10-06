import streamlit as st
import json
from helpers.helpers import (
    delete_field_and_rerun,
    export_schema,
    toggle_expand_schema,
    toggle_expand_schema_builder,
    next_id_for_schema,
    convert_repo_param_to_internal,
    pretty_schema_inline,
    update_repo_with_schema_usage
)
from helpers.storage import (
    read_repo,
    write_schema,
    write_repo,
    is_github_mode,
    get_current_branch,
    clear_cache,
    list_schemas,
)
from helpers.components import render_branch_selector, render_storage_status

def values_match(v1, v2, p_type):
    """Numeric-aware equality: '1' and '1.0' match for number fields."""
    if p_type == "number":
        try:
            return float(v1) == float(v2)
        except (TypeError, ValueError):
            return str(v1) == str(v2)
    return str(v1) == str(v2)


def has_value_check(field):
    return "value_contains" in field or field.get("value", "") not in ("", None)


def find_empty_match_value_errors(schema):
    """Value-checked fields must have a non-empty value; checked across all rows."""
    errors = []
    for field_id, field in schema.items():
        if field_id in (0, 1):
            continue
        if field.get("type") == "array":
            array_name = field.get("key", "")
            for nf in (field.get("nestedSchema") or {}).values():
                if nf.get("type") in ("boolean", "number", "object"):
                    continue
                if "value" not in nf and "value_contains" not in nf:
                    continue
                val = nf.get("value_contains") if "value_contains" in nf else nf.get("value", "")
                if not str(val or "").strip():
                    errors.append(f"{array_name}.{nf.get('key', '')}")
        elif field.get("type") not in ("array", "boolean", "number"):
            if "value" not in field and "value_contains" not in field:
                continue
            val = field.get("value_contains") if "value_contains" in field else field.get("value", "")
            if not str(val or "").strip():
                errors.append(field.get("key", ""))
    return errors


def build_grouped_dependency_options(repo, schema, current_cond_param, exclude_key=None):
    """Options for a 'Dependency Parameter' selectbox: params already used in
    this schema first (sorted), then the rest of the Repo (sorted) — every
    option stays fully, meaningfully selectable, no separator row involved.
    `exclude_key` drops the field being edited itself — a field can't
    meaningfully depend on its own presence/value. Returns (options, index,
    format_func) — pass format_func straight to st.selectbox to render the
    "already in schema" ones with a ✓ chip, purely a display-label thing."""
    schema_keys = {f.get("key") for f in schema.values() if f.get("key")}
    all_params = sorted(k for k in repo.keys() if k != exclude_key)
    if current_cond_param and current_cond_param not in all_params and current_cond_param != exclude_key:
        all_params.append(current_cond_param)

    in_schema = sorted(p for p in all_params if p in schema_keys)
    not_in_schema = sorted(p for p in all_params if p not in schema_keys)
    opts = [""] + in_schema + not_in_schema

    idx = opts.index(current_cond_param) if current_cond_param in opts else 0
    format_func = lambda p: f"✓ {p}" if p in schema_keys else (p if p else "—")
    return opts, idx, format_func


# RENDER READ-ONLY FIELD (NORMAL)

def render_schema_param(field_id, field):
    cols = st.columns([3, 2, 3, 1])

    # Compare with Repo default
    repo = st.session_state.get("repo", {})
    param_name = field.get("key", "")
    repo_default = repo.get(param_name, {}).get("value", "")

    # Bumped on every ↺ reset so the value/match/case-sensitive widgets get
    # a brand-new key and can't keep showing their last-committed state —
    # popping session_state alone was not enough to make the Match radio
    # (and the case-sensitive checkbox) forget "Contains" after a reset.
    reset_epoch = st.session_state.get(f"schema_reset_epoch_{field_id}", 0)

    # Only string fields support the Exact/Contains match mode.
    is_contains_mode = field.get("type") not in ("array", "boolean", "number") and "value_contains" in field

    # Robust comparison (0.0 vs 0)
    current_val = field.get("value_contains", "") if is_contains_mode else field.get("value", "")

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
        new_val = cols[2].selectbox("Value", opts, index=curr_idx, key=f"schema_value_{field_id}_{reset_epoch}")
        if new_val != str(current_val):
            field["value"] = new_val
            st.session_state.schema[field_id] = field
    elif field.get("type") == "number":
        # Use text_input to allow empty values for numbers
        new_val = cols[2].text_input("Value (number)", value=str(current_val) if current_val is not None else "", key=f"schema_value_{field_id}_{reset_epoch}")
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
        with cols[2]:
            check_value = st.toggle(
                "Check value",
                value=has_value_check(field),
                key=f"schema_check_value_{field_id}_{reset_epoch}",
                help="Off: only the type is validated. On: value must match exactly or contain a substring.",
            )
            if check_value:
                match_mode = st.radio(
                    "Match", ["Exact", "Contains"], index=(1 if is_contains_mode else 0),
                    key=f"schema_match_{field_id}_{reset_epoch}", horizontal=True,
                    help="Exact: value must match exactly. Contains: value must contain this substring.",
                )
                value_label = "Value" if match_mode == "Exact" else "Contains"
                new_val = st.text_input(value_label, str(current_val), key=f"schema_value_{field_id}_{reset_epoch}")
                if not new_val.strip():
                    st.error(f"{value_label} cannot be empty.")
                if match_mode == "Contains":
                    case_sensitive = st.checkbox(
                        "Case sensitive",
                        value=field.get("value_contains_case_sensitive", True),
                        key=f"schema_case_sensitive_{field_id}_{reset_epoch}",
                    )
            else:
                st.caption("Type only — no value check.")

        if check_value:
            desired_key = "value_contains" if match_mode == "Contains" else "value"
            stale_key = "value" if match_mode == "Contains" else "value_contains"
            if desired_key not in field or field.get(desired_key) != new_val or stale_key in field:
                field[desired_key] = new_val
                field.pop(stale_key, None)
                st.session_state.schema[field_id] = field
            if match_mode == "Contains":
                if field.get("value_contains_case_sensitive", True) != case_sensitive:
                    field["value_contains_case_sensitive"] = case_sensitive
                    st.session_state.schema[field_id] = field
            elif "value_contains_case_sensitive" in field:
                field.pop("value_contains_case_sensitive", None)
                st.session_state.schema[field_id] = field
        elif any(k in field for k in ("value", "value_contains", "value_contains_case_sensitive")):
            for k in ("value", "value_contains", "value_contains_case_sensitive"):
                field.pop(k, None)
            st.session_state.schema[field_id] = field

    # Recompute against the value as edited this run (not the pre-edit value
    # captured above) — otherwise the override state always lags one edit behind.
    post_edit_is_contains = field.get("type") not in ("array", "boolean", "number") and "value_contains" in field
    post_edit_val = field.get("value_contains", "") if post_edit_is_contains else field.get("value", "")
    has_repo_default = repo_default not in ("", None, [], "Any")
    # Repo defaults are always Exact-match values — Contains mode has no
    # repo-default equivalent, so using it is itself an override even when
    # the typed substring happens to equal the repo default's text.
    #
    # differs_from_repo is deliberately broader than "has a meaningful
    # default": even when the repo has nothing recommended (blank/Any), an
    # accidental edit still needs a way back — there'd otherwise be no
    # revert path at all for a parameter with no repo default.
    differs_from_repo = param_name in repo and (
        post_edit_is_contains or not values_match(post_edit_val, repo_default, field.get("type"))
    )
    is_overridden = has_repo_default and differs_from_repo

    label = f"Field {'[override]' if is_overridden else ''}"
    cols[0].text_input(label, param_name, disabled=True, key=f"schema_key_{field_id}")
    if is_overridden:
        cols[0].caption(f":orange[This parameter has a default value set in the repo ({repo_default}). Click ↺ to reset to it.]")
    elif differs_from_repo:
        cols[0].caption(":gray[Differs from what's currently in the repo for this parameter (no default set there). Click ↺ to revert.]")

    # Actions: Reset and Delete (icon-only — column is too narrow for "Reset" as text)
    if differs_from_repo:
        if cols[3].button("↺", key=f"schema_reset_{field_id}", help="Revert to repo's current value"):
            field["value"] = repo_default
            field.pop("value_contains", None)
            field.pop("value_contains_case_sensitive", None)
            st.session_state.schema[field_id] = field
            # Bump the reset epoch so the value/match/case-sensitive widgets
            # get fresh keys next render — popping their old keys wasn't
            # enough to make the Match radio forget "Contains".
            st.session_state[f"schema_reset_epoch_{field_id}"] = reset_epoch + 1
            st.toast(f"Reverted '{param_name}' to repo's current value.")
            st.rerun()

    if cols[3].button("X", key=f"schema_delete_{field_id}"):
        delete_field_and_rerun(field_id)

    # Advanced Label Logic
    adv_label = "Advanced"
    current_vip = field.get("validate_if_present", "")

    # Sticky expanded state: st.expander only re-forces `expanded` on the
    # frontend when the value we pass actually changes between reruns, so
    # once a missing-dependency warning flips this True we stop touching it
    # again — otherwise fixing the warning (dep now found) would flip
    # `expanded` back to False and yank the box shut mid-edit.
    expanded_key = f"adv_expanded_{field_id}"
    st.session_state.setdefault(expanded_key, False)

    if current_vip:
         dep_check = next((f for f in st.session_state.schema.values() if f.get("key") == current_vip), None)
         if not dep_check:
             adv_label += " ⚠️ (Missing Dep)"
             st.session_state[expanded_key] = True
         elif dep_check.get("optional") is True:
             adv_label += " ℹ️ (Dep Optional)"

    with st.expander(adv_label, expanded=st.session_state[expanded_key]):
        c_adv = st.columns(2)
        
        repo = st.session_state.get("repo", {})

        # 1. Determine Current Mode
        current_mode = "Required (Always)"
        current_vi = field.get("validate_if", {})
        
        if current_vi and current_vi.get("field") and current_vi.get("value"):
             current_mode = "Conditional (Required Value)"
        elif current_vip:
             current_mode = "Conditional (Dependent Present)"
        elif field.get("optional"):
             current_mode = "Optional"
             
        mode_options = ["Required (Always)", "Optional", "Conditional (Dependent Present)", "Conditional (Required Value)"]
        
        # 2. Render Mode Selector
        new_mode = st.radio("Validation Requirement", options=mode_options, index=mode_options.index(current_mode), key=f"mode_{field_id}", horizontal=True)
        
        # 3. Handle Conditional Dependency Input
        target_vip = ""
        target_vi_val = ""
        dep_type = "string"
        
        if new_mode in ["Conditional (Dependent Present)", "Conditional (Required Value)"]:
             current_cond_param = current_vi.get("field", "") if new_mode == "Conditional (Required Value)" else current_vip
             p_opts, v_idx, fmt = build_grouped_dependency_options(repo, st.session_state.schema, current_cond_param, exclude_key=param_name)
             target_vip = st.selectbox("Dependency Parameter", options=p_opts, index=v_idx, format_func=fmt, key=f"vip_sel_{field_id}", help="Validation runs ONLY if this parameter meets the condition.")

             if target_vip in repo:
                 dep_type = repo[target_vip].get("type", "string")

             if not target_vip:
                 st.warning("⚠️ No dependency selected. This field will behave as 'Optional'.")
                 
             if new_mode == "Conditional (Required Value)" and target_vip:
                  cv = current_vi.get("value", "")
                  
                  if dep_type == "boolean":
                      bool_opts = ["true", "false"]
                      cv_str = str(cv).lower() if not isinstance(cv, list) else str(cv[0]).lower()
                      b_idx = bool_opts.index(cv_str) if cv_str in bool_opts else 0
                      target_vi_val = st.selectbox("Expected Value (boolean)", bool_opts, index=b_idx, key=f"vi_val_{field_id}")
                  elif dep_type == "number":
                      try:
                          c_val_num = float(cv[0] if isinstance(cv, list) else cv)
                      except (ValueError, TypeError, IndexError):
                          c_val_num = 0.0
                      target_vi_val = st.number_input("Expected Value (number)", value=c_val_num, key=f"vi_val_{field_id}")
                  else:
                      if isinstance(cv, list):
                          cv = ", ".join(cv)
                      target_vi_val = st.text_input("Expected Value(s) (string) — comma separate for multiple", value=str(cv), key=f"vi_val_{field_id}")
        
        # 4. Update Schema State Logic
        new_is_opt = False
        new_vip_val = ""
        new_vi_dict = {}
        
        if new_mode == "Optional":
             new_is_opt = True
        elif new_mode == "Conditional (Dependent Present)":
             new_is_opt = True 
             new_vip_val = target_vip
        elif new_mode == "Conditional (Required Value)":
             new_is_opt = True
             if target_vip and str(target_vi_val).strip() != "":
                 if dep_type == "number":
                     try:
                         val_to_save = float(target_vi_val) if "." in str(target_vi_val) else int(target_vi_val)
                     except:
                         val_to_save = target_vi_val
                 elif dep_type == "boolean":
                     val_to_save = True if str(target_vi_val).lower() == "true" else False
                 else:
                     parsed = [v.strip() for v in str(target_vi_val).split(",") if v.strip()]
                     val_to_save = parsed[0] if len(parsed) == 1 else parsed
                     
                 if val_to_save is not None and str(val_to_save).strip() != "":
                     new_vi_dict = {"field": target_vip, "value": val_to_save}
             
        has_changed = False
        if field.get("optional", False) != new_is_opt:
             field["optional"] = new_is_opt
             has_changed = True
             
        if field.get("validate_if_present", "") != new_vip_val:
             field["validate_if_present"] = new_vip_val
             has_changed = True
             
        if str(field.get("validate_if", {})) != str(new_vi_dict):
             if new_vi_dict:
                 field["validate_if"] = new_vi_dict
             else:
                 field.pop("validate_if", None)
             has_changed = True
             
        if has_changed:
             st.session_state.schema[field_id] = field
             st.rerun()

        # Resolution Actions (Dependency Missing check)
        new_vip = field.get("validate_if_present", "") or field.get("validate_if", {}).get("field", "")
        if new_vip:
             dep_field = next((f for f in st.session_state.schema.values() if f.get("key") == new_vip), None)

        # Resolution Actions (inside expander)
        if new_vip:
             dep_field = next((f for f in st.session_state.schema.values() if f.get("key") == new_vip), None)
             
             if not dep_field:
                  st.warning(f"Dependency '{new_vip}' is not in this schema yet.")
                  if st.button(f"➕ Add '{new_vip}' to schema", key=f"add_dep_{field_id}"):
                       # Start Auto-Add Logic
                       if new_vip in repo:
                            new_internal = convert_repo_param_to_internal(new_vip, repo[new_vip])
                            new_sch_id = next_id_for_schema()
                            st.session_state.schema[new_sch_id] = new_internal
                            st.rerun()
                       else:
                            st.error(f"Cannot find '{new_vip}' in Repo.")
             
             elif dep_field.get("optional") is True:
                  st.info(f"ℹ️ Dependency '{new_vip}' is optional. Validation will be skipped if '{new_vip}' is missing.")

    st.markdown("---")


# RENDER READ-ONLY ARRAY FIELD
def render_array_param(field_id, field):
    nested = field.get("nestedSchema", {}) or {}
    # Compare nested with Repo
    repo = st.session_state.get("repo", {})
    array_name = field.get("key", "")
    repo_nested = repo.get(array_name, {}).get("nestedSchema", {})

    top = st.columns([4, 1, 2, 1])
    with top[0]:
        st.markdown(f"### Array: `{field.get('key')}`")
        exp_key = f"array_expanded_{field_id}"
        st.session_state.setdefault(exp_key, True)
    # Toggle
    if top[1].button("Collapse" if st.session_state[exp_key] else "Expand", key=f"toggle_arr_{field_id}"):
        st.session_state[exp_key] = not st.session_state[exp_key]
        st.rerun()

    # Reserved now, filled in after the loop below — filling it here would
    # read pre-edit state and lag a render behind, same bug as the per-field
    # ↺ had before it was fixed.
    reset_all_slot = top[2].empty()

    # Delete
    if top[3].button("X", key=f"delete_arr_{field_id}"):
        delete_field_and_rerun(field_id)
        st.stop()

    if not st.session_state[exp_key]:
        st.markdown("---")
        return

    st.markdown("#### Nested fields:")

    any_nested_overridden = False
    for nid, nf in sorted(nested.items()):
        cols = st.columns([3, 2, 3, 1])
        n_key = nf.get("key", "")

        # Only string nested fields support the Exact/Contains match mode.
        is_n_contains_mode = nf.get("type") not in ("boolean", "number", "object") and "value_contains" in nf

        # Check override for nested
        r_nf = repo_nested.get(n_key, {})
        r_val = r_nf.get("value", "")
        current_n_val = nf.get("value_contains", "") if is_n_contains_mode else nf.get("value", "")

        # See the matching comment in render_schema_param — this is bumped
        # on ↺ so the value/match/case-sensitive widgets can't keep showing
        # their last-committed state after a reset.
        n_reset_epoch = st.session_state.get(f"arr_nested_reset_epoch_{field_id}_{nid}", 0)

        cols[1].text_input("Type", nf.get("type", ""), disabled=True, key=f"arr_nested_type_{field_id}_{nid}")

        # Type-specific nested values
        if nf.get("type") == "boolean":
            opts = ["true", "false", "Any"]
            c_val = str(nf.get("value", "")).lower()
            c_idx = opts.index(c_val) if c_val in opts else 2
            new_n_val = cols[2].selectbox("Value", opts, index=c_idx, key=f"arr_nested_value_{field_id}_{nid}_{n_reset_epoch}")
            if new_n_val != nf.get("value", ""):
                nf["value"] = new_n_val
                st.session_state.schema[field_id]["nestedSchema"][nid] = nf
        elif nf.get("type") == "number":
            new_n_val = cols[2].text_input("Value (number)", value=str(nf.get("value", "")) if nf.get("value") is not None else "", key=f"arr_nested_value_{field_id}_{nid}_{n_reset_epoch}")
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
        elif nf.get("type") == "object":
            cols[2].markdown("—")
        else:
            with cols[2]:
                n_check_value = st.toggle(
                    "Check value",
                    value=has_value_check(nf),
                    key=f"arr_nested_check_value_{field_id}_{nid}_{n_reset_epoch}",
                    help="Off: only the type is validated. On: value must match exactly or contain a substring.",
                )
                if n_check_value:
                    n_match_mode = st.radio(
                        "Match", ["Exact", "Contains"], index=(1 if is_n_contains_mode else 0),
                        key=f"arr_nested_match_{field_id}_{nid}_{n_reset_epoch}", horizontal=True,
                        help="Exact: value must match exactly. Contains: value must contain this substring.",
                    )
                    n_value_label = "Value" if n_match_mode == "Exact" else "Contains"
                    new_n_val = st.text_input(n_value_label, str(current_n_val), key=f"arr_nested_value_{field_id}_{nid}_{n_reset_epoch}")
                    if not new_n_val.strip():
                        st.error(f"{n_value_label} cannot be empty.")
                    if n_match_mode == "Contains":
                        n_case_sensitive = st.checkbox(
                            "Case sensitive",
                            value=nf.get("value_contains_case_sensitive", True),
                            key=f"arr_nested_case_sensitive_{field_id}_{nid}_{n_reset_epoch}",
                        )
                else:
                    st.caption("Type only — no value check.")

            if n_check_value:
                n_desired_key = "value_contains" if n_match_mode == "Contains" else "value"
                n_stale_key = "value" if n_match_mode == "Contains" else "value_contains"
                if n_desired_key not in nf or nf.get(n_desired_key) != new_n_val or n_stale_key in nf:
                    nf[n_desired_key] = new_n_val
                    nf.pop(n_stale_key, None)
                    st.session_state.schema[field_id]["nestedSchema"][nid] = nf
                if n_match_mode == "Contains":
                    if nf.get("value_contains_case_sensitive", True) != n_case_sensitive:
                        nf["value_contains_case_sensitive"] = n_case_sensitive
                        st.session_state.schema[field_id]["nestedSchema"][nid] = nf
                elif "value_contains_case_sensitive" in nf:
                    nf.pop("value_contains_case_sensitive", None)
                    st.session_state.schema[field_id]["nestedSchema"][nid] = nf
            elif any(k in nf for k in ("value", "value_contains", "value_contains_case_sensitive")):
                for k in ("value", "value_contains", "value_contains_case_sensitive"):
                    nf.pop(k, None)
                st.session_state.schema[field_id]["nestedSchema"][nid] = nf

        # Recompute against the value as edited this run — see the matching
        # comment in render_schema_param for why this can't happen earlier.
        post_edit_n_is_contains = nf.get("type") not in ("boolean", "number", "object") and "value_contains" in nf
        post_edit_n_val = nf.get("value_contains", "") if post_edit_n_is_contains else nf.get("value", "")
        has_repo_default_n = r_val not in ("", None, [], "Any")
        # Same reasoning as the top-level check: broader than "has a
        # meaningful default" so an accidental edit is still revertable even
        # when the repo has nothing recommended for this nested key.
        n_differs_from_repo = n_key in repo_nested and (
            post_edit_n_is_contains or not values_match(post_edit_n_val, r_val, nf.get("type"))
        )
        is_n_overridden = has_repo_default_n and n_differs_from_repo
        any_nested_overridden = any_nested_overridden or n_differs_from_repo

        label = f"Key {'[override]' if is_n_overridden else ''}"
        cols[0].text_input(label, n_key, disabled=True, key=f"arr_nested_key_{field_id}_{nid}")
        if is_n_overridden:
            cols[0].caption(f":orange[This parameter has a default value set in the repo ({r_val}). Click ↺ to reset to it.]")
        elif n_differs_from_repo:
            cols[0].caption(":gray[Differs from what's currently in the repo for this key (no default set there). Click ↺ to revert.]")

        if n_differs_from_repo:
            if cols[3].button("↺", key=f"arr_nested_reset_{field_id}_{nid}", help="Revert to repo's current value"):
                nf["value"] = r_val
                nf.pop("value_contains", None)
                nf.pop("value_contains_case_sensitive", None)
                st.session_state.schema[field_id]["nestedSchema"][nid] = nf
                st.session_state[f"arr_nested_reset_epoch_{field_id}_{nid}"] = n_reset_epoch + 1
                st.rerun()
        # Nested Advanced Label Logic
        n_adv_label = f"Advanced ({n_key})"
        n_vip = nf.get("validate_if_present", "")

        # Sticky expanded state — see the top-level field's identical comment above.
        n_expanded_key = f"adv_expanded_{field_id}_{nid}"
        st.session_state.setdefault(n_expanded_key, False)

        if n_vip:
             # Check root schema for dependency
             dep_check_n = next((f for f in st.session_state.schema.values() if f.get("key") == n_vip), None)
             if not dep_check_n:
                 n_adv_label += " ⚠️ (Missing Dep)"
                 st.session_state[n_expanded_key] = True
             elif dep_check_n.get("optional") is True:
                 n_adv_label += " ℹ️ (Dep Optional)"

        with st.expander(n_adv_label, expanded=st.session_state[n_expanded_key]):
             c_n_adv = st.columns(2)
             
             # 2. Nest Vip Select (Prepare options)
             repo = st.session_state.get("repo", {})

             # UX SIMPLIFICATION (Nested)
             # 1. Determine Mode
             n_mode = "Required (Always)"
             n_vi = nf.get("validate_if", {})
             
             if n_vi and n_vi.get("field") and n_vi.get("value"):
                  n_mode = "Conditional (Required Value)"
             elif n_vip:
                  n_mode = "Conditional (Dependent Present)"
             elif nf.get("optional"):
                  n_mode = "Optional"
             
             n_opts = ["Required (Always)", "Optional", "Conditional (Dependent Present)", "Conditional (Required Value)"]
             new_n_mode = st.radio("Validation Requirement", options=n_opts, index=n_opts.index(n_mode), key=f"n_mode_{field_id}_{nid}", horizontal=True)
             
             # 2. Dependency Input
             n_target_vip = ""
             n_target_vi_val = ""
             n_dep_type = "string"
             
             if new_n_mode in ["Conditional (Dependent Present)", "Conditional (Required Value)"]:
                 repo = st.session_state.get("repo", {})
                 n_current_cond_param = n_vi.get("field", "") if new_n_mode == "Conditional (Required Value)" else n_vip
                 np_opts, nvip_idx, n_fmt = build_grouped_dependency_options(repo, st.session_state.schema, n_current_cond_param, exclude_key=n_key)
                 n_target_vip = st.selectbox("Dependency Parameter", options=np_opts, index=nvip_idx, format_func=n_fmt, key=f"n_vip_sel_{field_id}_{nid}")

                 if n_target_vip in repo:
                     n_dep_type = repo[n_target_vip].get("type", "string")

                 if not n_target_vip:
                     st.warning("⚠️ No dependency selected. This field will behave as 'Optional'.")
                     
                 if new_n_mode == "Conditional (Required Value)" and n_target_vip:
                      ncv = n_vi.get("value", "")
                      
                      if n_dep_type == "boolean":
                          n_bool_opts = ["true", "false"]
                          ncv_str = str(ncv).lower() if not isinstance(ncv, list) else str(ncv[0]).lower()
                          nb_idx = n_bool_opts.index(ncv_str) if ncv_str in n_bool_opts else 0
                          n_target_vi_val = st.selectbox("Expected Value (boolean)", n_bool_opts, index=nb_idx, key=f"n_vi_val_{field_id}_{nid}")
                      elif n_dep_type == "number":
                          try:
                              n_val_num = float(ncv[0] if isinstance(ncv, list) else ncv)
                          except (ValueError, TypeError, IndexError):
                              n_val_num = 0.0
                          n_target_vi_val = st.number_input("Expected Value (number)", value=n_val_num, key=f"n_vi_val_{field_id}_{nid}")
                      else:
                          if isinstance(ncv, list):
                              ncv = ", ".join(ncv)
                          n_target_vi_val = st.text_input("Expected Value(s) (string) — comma separate for multiple", value=str(ncv), key=f"n_vi_val_{field_id}_{nid}")

             # 3. Update Logic
             n_new_opt = False
             n_new_vip_val = ""
             n_new_vi_dict = {}
             
             if new_n_mode == "Optional":
                  n_new_opt = True
             elif new_n_mode == "Conditional (Dependent Present)":
                  n_new_opt = True
                  n_new_vip_val = n_target_vip
             elif new_n_mode == "Conditional (Required Value)":
                  n_new_opt = True
                  if n_target_vip and str(n_target_vi_val).strip() != "":
                      if n_dep_type == "number":
                          try:
                              n_val_to_save = float(n_target_vi_val) if "." in str(n_target_vi_val) else int(n_target_vi_val)
                          except:
                              n_val_to_save = n_target_vi_val
                      elif n_dep_type == "boolean":
                          n_val_to_save = True if str(n_target_vi_val).lower() == "true" else False
                      else:
                          n_parsed = [v.strip() for v in str(n_target_vi_val).split(",") if v.strip()]
                          n_val_to_save = n_parsed[0] if len(n_parsed) == 1 else n_parsed
                          
                      if n_val_to_save is not None and str(n_val_to_save).strip() != "":
                          n_new_vi_dict = {"field": n_target_vip, "value": n_val_to_save}
             
             n_changed = False
             if nf.get("optional", False) != n_new_opt:
                  nf["optional"] = n_new_opt
                  n_changed = True
             if nf.get("validate_if_present", "") != n_new_vip_val:
                  nf["validate_if_present"] = n_new_vip_val
                  n_changed = True
             if str(nf.get("validate_if", {})) != str(n_new_vi_dict):
                  if n_new_vi_dict:
                      nf["validate_if"] = n_new_vi_dict
                  else:
                      nf.pop("validate_if", None)
                  n_changed = True
             
             if n_changed:
                  st.session_state.schema[field_id]["nestedSchema"][nid] = nf
                  st.rerun()

             # Warning Checks
             n_new_vip = nf.get("validate_if_present", "") or nf.get("validate_if", {}).get("field", "")

             if n_new_vip:
                  dep_field_n = next((f for f in st.session_state.schema.values() if f.get("key") == n_new_vip), None)
                  
                  if not dep_field_n:
                       st.warning(f"Dependency '{n_new_vip}' missing.")
                       if st.button(f"➕ Add '{n_new_vip}'", key=f"add_dep_n_{field_id}_{nid}"):
                            if n_new_vip in repo:
                                 new_int = convert_repo_param_to_internal(n_new_vip, repo[n_new_vip])
                                 n_sch_id = next_id_for_schema()
                                 st.session_state.schema[n_sch_id] = new_int
                                 st.rerun()
                  
                  elif dep_field_n.get("optional") is True:
                      st.info(f"ℹ️ Dependency '{n_new_vip}' is optional. Validation will be skipped if '{n_new_vip}' is missing.")

    if any_nested_overridden:
        if reset_all_slot.button(
            "↺ Revert overridden fields to repo", key=f"arr_reset_all_{field_id}",
            help="Reverts every nested field that differs from what's currently in the repo — "
                 "including fields with no repo default, which revert back to empty.",
        ):
            for nid, nf in nested.items():
                n_key_ = nf.get("key", "")
                if n_key_ in repo_nested:
                    r_val = repo_nested.get(n_key_, {}).get("value", "")
                    nf["value"] = r_val
                    nf.pop("value_contains", None)
                    nf.pop("value_contains_case_sensitive", None)
                    st.session_state.schema[field_id]["nestedSchema"][nid] = nf
                    epoch_key = f"arr_nested_reset_epoch_{field_id}_{nid}"
                    st.session_state[epoch_key] = st.session_state.get(epoch_key, 0) + 1
            st.toast(f"Reverted all differing nested fields of '{array_name}' to repo.")
            st.rerun()

    st.markdown("---")


# MAIN BUILDER UI
def render_builder():
    st.title("Schema Builder")

    # Branch selector for GitHub mode
    if is_github_mode():
        col_branch, col_status = st.columns([2, 3])
        with col_branch:
            render_branch_selector(key="builder_branch", compact=True)
        with col_status:
            render_storage_status()

    st.session_state.setdefault("expanded_schema", True)
    st.session_state.setdefault("expanded_schema_builder", True)

    # Load repo from storage (GitHub or GCS)
    try:
        repo = read_repo() or {}
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
        if st.button("✏️ Change name", key="change_event_name_btn"):
            st.session_state.event_name = ""
            st.rerun()

    existing_schema_files = set(list_schemas())
    current_name = st.session_state.event_name.strip()
    if current_name and current_name != st.session_state.get("loaded_schema_name"):
        st.session_state.pop("loaded_schema_name", None)
    is_editing_loaded_schema = (
        st.session_state.event_name.strip()
        and st.session_state.event_name.strip() == st.session_state.get("loaded_schema_name")
    )
    event_name_conflict = bool(
        st.session_state.event_name
        and f"{st.session_state.event_name.strip()}.json" in existing_schema_files
        and not is_editing_loaded_schema
    )
    st.session_state.event_name_conflict = event_name_conflict
    if event_name_conflict:
        st.error(
            f"A schema named '{st.session_state.event_name}' already exists. "
            "The builder only creates new events — pick a different name to avoid "
            "overwriting the existing schema."
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
    real_categories = sorted({param.get("category") for param in repo.values() if param.get("category")})
    has_uncategorized = any(not param.get("category") for param in repo.values())
    category_options = ["All"] + ([""] if has_uncategorized else []) + real_categories
    selected_category = st.selectbox(
        "Category", category_options, key="category_filter",
        format_func=lambda c: "— No category —" if c == "" else c,
    )

    # Search filter
    query = st.text_input("Search parameter", key="search_param")

    # Remove already used keys
    used = {f.get("key") for f in schema.values()}
    available = [k for k in repo.keys() if k not in used]

    # Apply category filter
    if selected_category != "All":
        available = [k for k in available if (repo[k].get("category") or "") == selected_category]

    # Apply search filter
    if query:
        available = [k for k in available if query.lower() in k.lower()]

    if not available:
        st.info("No parameters available with current filters.")

    selected = st.selectbox("Choose parameter", available, key="choose_param")

    if st.button("Add selected parameter", key="add_param_btn", disabled=not available):
        new_id = next_id_for_schema()
        internal = convert_repo_param_to_internal(selected, repo[selected])

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
                "Collapse fields" if st.session_state.expanded_schema_builder else "Expand fields",
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

        def handle_save(data, filename, event_name):
            """Save schema to storage (GitHub or GCS)."""
            # Write schema
            commit_msg = f"Update schema: {event_name}"
            success, message = write_schema(filename, data, commit_message=commit_msg)

            if success:
                st.session_state.upload_status = True
                st.session_state.loaded_schema_name = event_name
                # Update repo with schema usage
                update_repo_with_schema_usage(event_name, data)
                # Clear cache to refresh explorer
                clear_cache()
            else:
                st.session_state.upload_status = False
                st.session_state.upload_error = message

        empty_match_value_errors = find_empty_match_value_errors(schema)

        if event_name_conflict:
            st.button("Save to GCS" if not is_github_mode() else "Save to GitHub", disabled=True, key="send_gcp_btn")
        elif st.session_state.event_name.strip():
            # Determine button label based on storage mode
            if is_github_mode():
                current_branch = get_current_branch()
                btn_label = f"Save to GitHub ({current_branch})"
            else:
                btn_label = "Save to GCS"

            if empty_match_value_errors:
                st.error(
                    "Fix the empty Exact/Contains value(s) before saving: "
                    + ", ".join(empty_match_value_errors)
                )

            st.button(
                btn_label,
                on_click=handle_save,
                args=(export, f"{st.session_state.event_name}.json", st.session_state.event_name),
                type="primary",
                disabled=bool(empty_match_value_errors),
                key="send_gcp_btn",
            )

            # Show result
            if st.session_state.get("upload_status") is True:
                st.success("Schema saved successfully!")
                del st.session_state.upload_status
            elif st.session_state.get("upload_status") is False:
                st.error(f"Save failed: {st.session_state.get('upload_error', 'Unknown error')}")
                del st.session_state.upload_status
                st.session_state.pop("upload_error", None)
        else:
            st.error("Event name is required")

    # Toasts
    if st.session_state.get("toast_message"):
        st.toast(st.session_state.toast_message)
        st.session_state.toast_message = None
