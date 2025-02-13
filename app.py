import streamlit as st
from agents.product_owner import handle_file_upload
from agents.developer import generate_code
from agents.test_manager import generate_test_cases
from utils import (
    check_rally_config,
    upload_user_story_to_rally,
    config,
    test_rally_connection,
    get_rally_workspaces,
    get_rally_projects,
    get_rally_user_stories,
    get_user_story_test_data,
    get_project_rca_data
)
import openai
import pandas as pd
import plotly.express as px
import urllib3
import warnings
import plotly.graph_objects as go
from typing import Dict

# Define OPENAI_MODELS right here, after imports
OPENAI_MODELS = {
    "gpt-4": {
        "description": "Most capable model, best for complex tasks",
        "context_length": "8,192 tokens",
        "training_data": "Up to Sep 2023"
    },
    "gpt-4-turbo": {
        "description": "Latest GPT-4 model with improved performance",
        "context_length": "128,000 tokens",
        "training_data": "Up to Dec 2023"
    },
    "gpt-3.5-turbo": {
        "description": "Fast and cost-effective for most tasks",
        "context_length": "4,096 tokens",
        "training_data": "Up to Sep 2023"
    },
    "gpt-3.5-turbo-16k": {
        "description": "Same as 3.5-turbo with extended context",
        "context_length": "16,384 tokens",
        "training_data": "Up to Sep 2023"
    }
}

# Initialize session state for openai_model
if 'openai_model' not in st.session_state:
    st.session_state.openai_model = "gpt-4"

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
openai.api_key = 'your-api-key-here'
 
# Configure page settings
st.set_page_config(
    page_title="SDLC Agent Orchestrator",
    page_icon="🤖",
    layout="wide"
)
 
# Sidebar logo and styling
st.sidebar.markdown("""
    <style>
        .logo-container {
            text-align: center;
            padding: 20px 10px;
            margin-bottom: 20px;
        }
       
        .logo-title {
            font-size: 28px;
            font-weight: 700;
            color: #1E88E5;
            margin: 0;
            padding: 0;
            letter-spacing: 3px;
            line-height: 1.2;
        }
       
        .logo-subtitle {
            font-size: 16px;
            color: #424242;
            margin: 8px 0 0 0;
            letter-spacing: 4px;
            text-transform: uppercase;
            font-weight: 500;
        }
       
        hr.separator {
            margin: 24px 0;
            border: none;
            height: 2px;
            background: #f0f0f0;
        }
       
        .menu-header {
            font-size: 16px;
            font-weight: 500;
            color: #333333;
            margin: 20px 0 10px 0;
        }
       
        /* Agent section headers styling */
        .agent-section-header {
            font-size: 16px;
            font-weight: 500;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 6px;
            background: linear-gradient(to right, #F7FAFC, #EDF2F7);
        }
       
        .task-agents-header {
            color: #3B82F6;
        }
       
        .ops-agents-header {
            color: #8B5CF6;
        }
    </style>
   
    <div class="logo-container">
        <div class="logo-title">SDLC AGENT</div>
        <div class="logo-subtitle">Orchestrator</div>
    </div>
    <hr class="separator">
""", unsafe_allow_html=True)
 
# Menu section in sidebar
st.sidebar.markdown("""
    <div class="menu-header">📋 Menu</div>
""", unsafe_allow_html=True)
 
# Add new session state initialization
if 'task_agents_enabled' not in st.session_state:
    st.session_state.task_agents_enabled = False
if 'ops_agents_enabled' not in st.session_state:
    st.session_state.ops_agents_enabled = False
 
def toggle_task_agents():
    if st.session_state.task_toggle:
        st.session_state.ops_toggle = False
        st.session_state.task_agents_enabled = True
        st.session_state.ops_agents_enabled = False
    else:
        st.session_state.task_agents_enabled = False
 
def toggle_ops_agents():
    if st.session_state.ops_toggle:
        st.session_state.task_toggle = False
        st.session_state.ops_agents_enabled = True
        st.session_state.task_agents_enabled = False
    else:
        st.session_state.ops_agents_enabled = False
 
# Update the agents section in sidebar
st.sidebar.markdown("""
    <div class="agent-section-header task-agents-header">
        Task Agents
    </div>
""", unsafe_allow_html=True)
 
# Add enable/disable toggle for Task Agents
task_agents_enabled = st.sidebar.toggle(
    "Enable Task Agents",
    value=st.session_state.task_agents_enabled,
    key="task_toggle",
    on_change=toggle_task_agents
)
 
if st.session_state.task_agents_enabled:
    selected_task = st.sidebar.selectbox(
        "Select Task Agents",
        [
            "👤 Product Owner Agent",
            "👨‍💻 Developer Agent",
            "🧪 Test Manager Agent"
        ]
    )
else:
    selected_task = None
 
st.sidebar.markdown("""
    <div class="agent-section-header ops-agents-header">
        Operation Agents
    </div>
""", unsafe_allow_html=True)
 
# Add enable/disable toggle for Operation Agents
ops_agents_enabled = st.sidebar.toggle(
    "Enable Operation Agents",
    value=st.session_state.ops_agents_enabled,
    key="ops_toggle",
    on_change=toggle_ops_agents
)
 
if st.session_state.ops_agents_enabled:
    selected_ops = st.sidebar.selectbox(
        "Select Ops Agent",
        [
            "🔍 Failure Analysis",
            "🎯 Root Cause Analysis"
        ]
    )
else:
    selected_ops = None
 
# Settings section in sidebar
st.sidebar.markdown("## ⚙️ Settings")
if st.sidebar.checkbox("Show Configuration"):
    st.sidebar.markdown("### 🔑 Rally Configuration")
    
    # Configuration inputs
    config["rally_endpoint"] = st.sidebar.text_input("Rally Endpoint", value=config.get("rally_endpoint", ""))
    config["rally_api_key"] = st.sidebar.text_input("Rally API Key", value=config.get("rally_api_key", ""), type="password")
    config["openai_api_key"] = st.sidebar.text_input("OpenAI API Key", value=config.get("openai_api_key", ""), type="password")
    
    # Add OpenAI logo and model configuration
    st.sidebar.markdown("""
        <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
            <img src='https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg' 
                 style='width: 30px; margin-right: 10px;'>
            <span style='font-size: 1.2em; font-weight: 600; color: #1a73e8;'>
                OpenAI Model Configuration
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    # Add custom CSS for model selector
    st.markdown("""
        <style>
        .model-selector {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        .model-header {
            font-size: 16px;
            font-weight: 500;
            color: #1a73e8;
            margin-bottom: 10px;
        }
        .model-description {
            font-size: 14px;
            color: #5f6368;
            margin: 5px 0;
        }
        .model-specs {
            font-size: 12px;
            color: #80868b;
            margin-top: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Add model selector
    st.sidebar.markdown("### 🤖 OpenAI Model Configuration")
    
    # Create columns for better layout
    col1, col2 = st.sidebar.columns([3, 1])
    
    with col1:
        selected_model = st.selectbox(
            "Select Model",
            options=list(OPENAI_MODELS.keys()),
            index=list(OPENAI_MODELS.keys()).index(st.session_state.openai_model),
            key="model_selector"
        )
    
    # Show model information in an expander
    with st.sidebar.expander("Model Details", expanded=True):
        st.markdown(f"""
            <div class="model-selector">
                <div class="model-header">{selected_model}</div>
                <div class="model-description">{OPENAI_MODELS[selected_model]['description']}</div>
                <div class="model-specs">
                    Context Length: {OPENAI_MODELS[selected_model]['context_length']}<br>
                    Training Data: {OPENAI_MODELS[selected_model]['training_data']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Update session state when model changes
    if selected_model != st.session_state.openai_model:
        st.session_state.openai_model = selected_model
   
    # Create container for buttons
    st.sidebar.markdown('<div class="button-container">', unsafe_allow_html=True)
    col1, col2 = st.sidebar.columns(2)
   
    with col1:
        if st.button("💾 Save"):
            st.sidebar.markdown('<div class="success-message">✅ Configuration saved!</div>', unsafe_allow_html=True)
   
    with col2:
        if st.button("🔗 Connect"):
            if check_rally_config():
                success, message = test_rally_connection(config["rally_endpoint"], config["rally_api_key"])
                if success:
                    st.sidebar.markdown(f'<div class="success-message">✅ {message}</div>', unsafe_allow_html=True)
                    workspaces = get_rally_workspaces()
                    if workspaces:
                        st.session_state['workspaces'] = workspaces
                else:
                    st.sidebar.error(message)
            else:
                st.sidebar.error("Please save Rally configuration first")
   
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
 
# Main content area with custom styling
st.markdown("""
    <style>
        .main .block-container {
            padding-top: 2rem;
        }
        h1, h2, h3 {
            color: #1D1D1F !important;  /* Apple-style dark gray */
            font-weight: 500;
        }
        .stButton button {
            background-color: #0071E3;  /* Apple-style blue */
            color: white;
            border-radius: 20px;
            padding: 0.5rem 1rem;
        }
        .stSelectbox label {
            color: #1D1D1F;
        }
        /* Modern button styling */
        .stButton button {
            background-color: #0071E3;
            color: white;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
            border: none;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s ease-in-out;
            width: 100%;
            margin: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
       
        .stButton button:hover {
            background-color: #0077ED;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transform: translateY(-1px);
        }
       
        .stButton button:active {
            transform: translateY(0px);
        }
       
        /* Container for buttons */
        .button-container {
            display: flex;
            gap: 10px;
            padding: 10px 0;
        }
       
        .button-container > div {
            flex: 1;
        }
       
        /* Success message styling */
        .success-message {
            margin-top: 8px;
            padding: 8px;
            border-radius: 6px;
            background-color: #f0f9f4;
            color: #1a7f37;
            font-size: 14px;
        }
       
        /* Toggle button styling */
        .stToggle {
            margin-bottom: 1rem;
        }
       
        .stToggle > label {
            font-weight: 500 !important;
            color: #333333 !important;
        }
       
        /* Disabled state styling */
        .disabled-agent {
            opacity: 0.5;
            pointer-events: none;
        }
       
        /* Add these new styles for metrics */
        .metric-container {
            padding: 10px;
        }
       
        .metric-label {
            font-size: 14px !important;
            overflow-wrap: break-word;
            word-wrap: break-word;
            word-break: break-word;
            max-width: 100%;
        }
       
        [data-testid="stMetricValue"] {
            font-size: 24px !important;
        }
       
        [data-testid="stMetricDelta"] {
            font-size: 12px !important;
        }
    </style>
""", unsafe_allow_html=True)
 
# Workspace and Project Selection
def show_workspace_project_selector():
    workspaces = st.session_state.get('workspaces', [])
    selected_workspace = None
    selected_project = None
   
    if workspaces:
        workspace_names = {w["name"]: w["id"] for w in workspaces}
        selected_workspace_name = st.selectbox("Select Workspace", list(workspace_names.keys()))
       
        if selected_workspace_name:
            selected_workspace = workspace_names[selected_workspace_name]
            projects = get_rally_projects(selected_workspace)
           
            if projects:
                project_names = {p["name"]: p["id"] for p in projects}
                selected_project_name = st.selectbox("Select Project", list(project_names.keys()))
               
                if selected_project_name:
                    selected_project = project_names[selected_project_name]
    else:
        st.warning("Please connect to Rally to fetch workspaces and projects")
   
    return selected_workspace, selected_project
 
# Handle main content based on selection
if st.session_state.task_agents_enabled and selected_task == "👤 Product Owner Agent":
    st.title("Product Owner Agent")
    uploaded_file = st.file_uploader("Upload Requirements Document", type=["txt", "pdf", "docx"])
    
    if uploaded_file:
        with st.spinner("Processing requirements..."):
            response = handle_file_upload(uploaded_file, model=st.session_state.openai_model)  # Pass selected model
            st.write(response)

elif st.session_state.task_agents_enabled and selected_task == "👨‍💻 Developer Agent":
    st.title("Developer Agent")
    user_story = st.text_area("Enter User Story")
    
    if st.button("Generate Code"):
        with st.spinner("Generating code..."):
            code = generate_code(user_story, model=st.session_state.openai_model)  # Pass selected model
            st.code(code)

elif st.session_state.task_agents_enabled and selected_task == "🧪 Test Manager Agent":
    st.title("Test Manager Agent")
    user_story = st.text_area("Enter User Story for Test Case Generation")
    
    if st.button("Generate Test Cases"):
        with st.spinner("Generating test cases..."):
            test_cases = generate_test_cases(user_story, model=st.session_state.openai_model)  # Pass selected model
            st.write(test_cases)

elif ops_agents_enabled and selected_ops == "🔍 Failure Analysis":
    st.title("Failure Analysis")
    failure_description = st.text_area("Describe the failure")
    
    if st.button("Analyze"):
        with st.spinner("Analyzing failure..."):
            analysis = analyze_failure(failure_description, model=st.session_state.openai_model)  # Pass selected model
            st.write(analysis)

elif ops_agents_enabled and selected_ops == "🎯 Root Cause Analysis":
    st.title("Root Cause Analysis")
    issue_description = st.text_area("Describe the issue")
    
    if st.button("Analyze Root Cause"):
        with st.spinner("Analyzing root cause..."):
            root_cause = analyze_root_cause(issue_description, model=st.session_state.openai_model)  # Pass selected model
            st.write(root_cause)

else:
    # Show welcome message when no agent is enabled
    st.title("Welcome to SDLC Agent Orchestrator")
    st.info("Please enable either Task Agents or Operation Agents to begin.")