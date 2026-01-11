import traceback
import streamlit as st
from streamlit_option_menu import option_menu
from builder import render_builder
from explorer import render_explorer    
from repo import render_repo
from home import render_home
from export import render_exporter
from validation_report import render_validation_report
import time
from dotenv import load_dotenv
load_dotenv()


st.set_page_config(page_title="Home", layout="wide")

st.session_state.setdefault("page", "home")
st.session_state.setdefault("upload_status", None)

st.session_state.setdefault("event_name", "")
st.session_state.setdefault("schema", {})
st.session_state.setdefault("schema_version", int(0))

pages = ["Home", "Explorer", "Builder", "Params Repo", "Export"]
# Map session state page to index
current_page = st.session_state.page.lower()
try:
    default_idx = [p.lower() for p in pages].index(current_page)
except ValueError:
    default_idx = 0

with st.container():
    selected = option_menu(
        None,
        ["Home", "Explorer", "Builder", "Params Repo", "Export", "Validation Report"],
        icons=["house", "list", "tools", "book", "file-earmark-arrow-up", "activity"],
        orientation="horizontal",
        default_index=default_idx,
        styles={
            "container": {"padding": "0!important", "margin": "0", "width": "100%"},
            "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "padding": "10px"},
        }
    )

# Only update if the user manually clicked the menu
if selected.lower() != st.session_state.page.lower():
    st.session_state.page = selected.lower()
    st.rerun()

try:    
    if st.session_state.page == "builder":
        render_builder()
    elif st.session_state.page == "explorer":
        render_explorer()
    elif st.session_state.page == "export":
        render_exporter()
    elif st.session_state.page == "params repo":
        render_repo()
    elif st.session_state.page == "home":
        render_home()
    elif st.session_state.page == "validation report":
        render_validation_report()

except Exception as e:
    import traceback
    st.error(f"An error occurred: {e}")
    print("TRACEBACK:", traceback.format_exc())
    err = traceback.format_exc()
    st.error(f"An error occurred while fetching schemas: {err}")
# ---------------------------------------------------