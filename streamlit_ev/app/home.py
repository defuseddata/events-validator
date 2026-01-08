import streamlit as st

def render_home():
    st.title("📦 Event Schema Manager")
    
    # Hero / Intro
    st.markdown("""
    Welcome to the **Event Schema Manager**. This application is your central hub for designing, 
    validating, and standardizing analytics event schemas across your organization.
    
    It combines a **Centralized Parameter Repository** with a flexible **Schema Builder** 
    and robust **GCP Synchronization**.
    """)
    
    st.divider()

    # Workflow High Level
    st.subheader("🚀 The Workflow")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### 1. Define")
        st.caption("Create reusable parameters in the **Repository**.")
    with c2:
        st.markdown("#### 2. Build")
        st.caption("Assemble schemas in the **Builder** using repo items.")
    with c3:
        st.markdown("#### 3. Deploy")
        st.caption("Export and upload valid JSON schemas to **GCP**.")
    with c4:
        st.markdown("#### 4. Audit")
        st.caption("Monitor schema health in the **Explorer**.")

    st.divider()
    
    # Detailed Features
    st.subheader("✨ Key Features")
    
    with st.container():
        col_repo, col_exp = st.columns(2)
        
        with col_repo:
            st.info("📚 **Parameters Repository**")
            st.markdown("""
            - **Single Source of Truth**: Define parameters once, use everywhere.
            - **Transactional Updates**: Editing a parameter triggers a *Safe Update Workflow*.
            - **Impact Analysis**: See which schemas will be affected before saving.
            - **Review & Apply**: Approve schema updates with a side-by-side Diff view.
            """)
            
        with col_exp:
            st.warning("🔍 **Schema Explorer**")
            st.markdown("""
            - **Cloud Storage Browser**: View schemas directly from your GCP bucket.
            - **Health Checks**: Automatically detects schemas that are out-of-sync with the Repo.
            - **One-Click Fix**: Update outdated schemas instantly from the UI.
            - **Load & Edit**: Pull any existing schema back into the Builder.
            """)
            
    with st.container():
        st.success("🔧 **Schema Builder**")
        st.markdown("""
        - **Visual Editor**: No need to write raw JSON.
        - **Type Safety**: Enforces types (String, Number, Boolean, Arrays, Objects).
        - **Nested Structures**: Easily create complex array schemas with nested objects.
        """)

    st.divider()
    st.caption("Ready to start? Select a module from the menu above.")
