import traceback
import streamlit as st
from streamlit_option_menu import option_menu
from builder import render_builder
from explorer import render_explorer    
from repo import render_repo
from home import render_home
from export import render_exporter
import time
from dotenv import load_dotenv
load_dotenv()


st.set_page_config(page_title="Home", layout="wide")

st.session_state.setdefault("page", "builder")
st.session_state.setdefault("upload_status", None)

st.session_state.setdefault("event_name", "")
st.session_state.setdefault("schema", {})
st.session_state.setdefault("schema_version", int(0))

with st.container():
    selected = option_menu(
        None,
        ["Home", "Explorer", "Builder", "Params Repo", "Export"],
        icons=["house", "list", "tools", "book", "file-earmark-arrow-up"],
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "margin": "0", "width": "100%"},
            "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "padding": "10px"},
        }
    )

if st.session_state.event_name:
    st.info(f'🛠️ Active Schema: **{st.session_state["event_name"]}** (v{st.session_state["schema_version"]})')

st.session_state.page = selected.lower()

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

except Exception as e:
    import traceback
    st.error(f"An error occurred: {e}")
    print("TRACEBACK:", traceback.format_exc())
    err = traceback.format_exc()
    st.error(f"An error occurred while fetching schemas: {err}")
# ---------------------------------------------------