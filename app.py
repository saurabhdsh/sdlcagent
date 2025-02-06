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
if task_agents_enabled and selected_task == "👤 Product Owner Agent":
    st.title("👤 Product Owner Agent")
    selected_workspace, selected_project = show_workspace_project_selector()
   
    if selected_workspace and selected_project:
        st.subheader("Upload Documents to Generate User Story")
        uploaded_file = st.file_uploader("Upload Requirement Document", type=["txt", "docx", "pdf"])
       
        if uploaded_file:
            st.success("File uploaded successfully!")
            user_story = handle_file_upload(uploaded_file, config.get("openai_api_key"))
           
            if user_story:
                st.success("User Story Generated Successfully!")
                st.code(user_story, language="markdown")
               
                if st.button("Upload to Rally"):
                    rally_response = upload_user_story_to_rally(user_story, selected_project)
                    if rally_response:
                        st.success(rally_response)
                    else:
                        st.error("Failed to upload user story to Rally")
 
elif task_agents_enabled and selected_task == "👨‍💻 Developer Agent":
    st.title("👨‍💻 Developer Agent")
    selected_workspace, selected_project = show_workspace_project_selector()
   
    if selected_workspace and selected_project:
        st.subheader("Generate Code from User Stories")
       
        # Fetch and display user stories
        user_stories = get_rally_user_stories(selected_workspace, selected_project)
        if user_stories:
            story_options = {story["display_name"]: story for story in user_stories}
            selected_story_name = st.selectbox("Select User Story", list(story_options.keys()))
           
            if selected_story_name:
                selected_story = story_options[selected_story_name]
                st.text_area("Story Description", selected_story["description"], height=150)
               
                language = st.selectbox("Select Programming Language", ["Python", "Java", "JavaScript", "C#"])
                prompt = st.text_area("Additional Requirements (Optional)")
               
                if st.button("Generate Code"):
                    generated_code = generate_code(selected_story["description"], language, prompt, config.get("openai_api_key"))
                    if generated_code:
                        st.success("Code Generated Successfully!")
                        st.code(generated_code, language=language.lower())
        else:
            st.info("No user stories found in the selected project")
 
elif task_agents_enabled and selected_task == "🧪 Test Manager Agent":
    st.title("🧪 Test Manager Agent")
    selected_workspace, selected_project = show_workspace_project_selector()
   
    if selected_workspace and selected_project:
        st.subheader("Generate Test Cases from User Stories")
       
        # Fetch and display user stories
        user_stories = get_rally_user_stories(selected_workspace, selected_project)
        if user_stories:
            story_options = {story["display_name"]: story for story in user_stories}
            selected_story_name = st.selectbox("Select User Story", list(story_options.keys()))
           
            if selected_story_name:
                selected_story = story_options[selected_story_name]
                st.text_area("Story Description", selected_story["description"], height=150)
               
                prompt = st.text_area("Additional Test Requirements (Optional)")
               
                if st.button("Generate Test Cases"):
                    test_cases = generate_test_cases(selected_story["description"], prompt, config.get("openai_api_key"))
                    if test_cases:
                        st.success("Test Cases Generated Successfully!")
                        st.code(test_cases, language="gherkin")
        else:
            st.info("No user stories found in the selected project")

elif ops_agents_enabled and selected_ops == "🔍 Failure Analysis":
    st.title("🔍 Failure Analysis")
    selected_workspace, selected_project = show_workspace_project_selector()
    
    if selected_workspace and selected_project:
        st.subheader("Select User Story")
        user_stories = get_rally_user_stories(selected_workspace, selected_project)
        
        if user_stories:
            story_options = {story["display_name"]: story for story in user_stories}
            selected_story_name = st.selectbox("Select User Story", list(story_options.keys()))
            
            if selected_story_name:
                selected_story = story_options[selected_story_name]
                test_data = get_user_story_test_data(selected_workspace, selected_project, selected_story["id"])
                
                if test_data and "test_cases" in test_data:
                    # Display test metrics in columns
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Total Test Cases", 
                            test_data.get("total_tests", 0)
                        )
                    
                    with col2:
                        pass_percentage = test_data.get("pass_percentage", 0)
                        st.metric(
                            "Passed Tests", 
                            test_data.get("passed", 0),
                            f"{pass_percentage:.1f}%"
                        )
                    
                    with col3:
                        fail_percentage = (test_data.get("failed", 0) / test_data.get("total_tests", 1) * 100) if test_data.get("total_tests", 0) > 0 else 0
                        st.metric(
                            "Failed Tests", 
                            test_data.get("failed", 0),
                            f"{fail_percentage:.1f}%"
                        )

                    # Display test cases table
                    st.subheader("Test Case Details")
                    if test_data["test_cases"]:
                        # Create DataFrame with reordered columns
                        df_tests = pd.DataFrame(test_data["test_cases"])
                        
                        # Ensure all required columns exist
                        required_columns = ['test_case_id', 'test_case_name', 'tcr_id', 'date_time', 'verdict']
                        for col in required_columns:
                            if col not in df_tests.columns:
                                df_tests[col] = 'N/A'
                        
                        # Select and rename columns for display
                        df_tests = df_tests[required_columns]
                        df_tests.columns = ['Test Case ID', 'Test Case Name', 'TCR ID', 'Date and Time', 'Verdict']
                        
                        # Sort by Test Case ID
                        df_tests = df_tests.sort_values('Test Case ID', ascending=True)
                        
                        # Apply styling with updated column names and better colors
                        styled_df = df_tests.style.apply(
                            lambda x: ['background-color: #e6ffe6; color: #2E7D32' if v == 'Pass'
                                      else 'background-color: #ffe6e6; color: #C62828' if v == 'Fail'
                                      else 'background-color: #fff3e0; color: #EF6C00' for v in x],
                            subset=['Verdict']
                        ).format({
                            'Date and Time': lambda x: x.split('T')[0] + ' ' + x.split('T')[1][:8] if 'T' in str(x) else x
                        })
                        
                        # Display the table
                        st.dataframe(styled_df, use_container_width=True)
                    
                    # Display defects table and charts
                    if test_data["defects"]:
                        st.subheader("Defect Analysis")
                        
                        # Create DataFrame for defects
                        df_defects = pd.DataFrame(test_data["defects"])
                        
                        # Create metrics for defect summary
                        total_defects = len(df_defects)
                        priority_counts = df_defects['priority'].value_counts()
                        severity_counts = df_defects['severity'].value_counts()
                        state_counts = df_defects['state'].value_counts()
                        
                        # Display defect metrics
                        st.markdown("### Defect Summary")
                        def_col1, def_col2, def_col3 = st.columns(3)
                        
                        with def_col1:
                            st.metric("Total Defects", total_defects)
                        with def_col2:
                            highest_priority = priority_counts.index[0] if not priority_counts.empty else "None"
                            st.metric("Most Common Priority", highest_priority, 
                                    f"{priority_counts.get(highest_priority, 0)} defects")
                        with def_col3:
                            highest_severity = severity_counts.index[0] if not severity_counts.empty else "None"
                            st.metric("Most Common Severity", highest_severity,
                                    f"{severity_counts.get(highest_severity, 0)} defects")
                        
                        # Create charts for defect distribution
                        def_chart_col1, def_chart_col2 = st.columns(2)
                        
                        with def_chart_col1:
                            # Priority distribution pie chart
                            fig_priority = px.pie(
                                values=priority_counts.values,
                                names=priority_counts.index,
                                title='Defects by Priority',
                                color_discrete_sequence=px.colors.qualitative.Set3
                            )
                            fig_priority.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_priority, use_container_width=True)
                        
                        with def_chart_col2:
                            # Severity distribution pie chart
                            fig_severity = px.pie(
                                values=severity_counts.values,
                                names=severity_counts.index,
                                title='Defects by Severity',
                                color_discrete_sequence=px.colors.qualitative.Set2
                            )
                            fig_severity.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_severity, use_container_width=True)
                        
                        # State distribution bar chart
                        st.markdown("### Defect State Distribution")
                        fig_state = px.bar(
                            x=state_counts.index,
                            y=state_counts.values,
                            title='Defects by State',
                            labels={'x': 'State', 'y': 'Number of Defects'},
                            color=state_counts.values,
                            color_continuous_scale='Viridis'
                        )
                        st.plotly_chart(fig_state, use_container_width=True)
                        
                        # Display detailed defects table with styling
                        st.markdown("### Defect Details")
                        st.dataframe(
                            df_defects.style.apply(lambda x: [
                                'background-color: #ffebee' if v == 'High' 
                                else 'background-color: #fff3e0' if v == 'Medium'
                                else 'background-color: #f1f8e9' if v == 'Low'
                                else '' for v in x
                            ], subset=['priority', 'severity']),
                            use_container_width=True
                        )
                    else:
                        st.info("No defects found for this user story")
                    
                    # Continue with existing Azure System Failure Section
                    st.subheader("Azure System Failure Analysis")
                    failure_description = st.text_area("Describe the failure scenario", height=150)
                    system_context = st.text_area("Provide system context (Optional)", height=100)
                    
                    if st.button("Analyze Failure"):
                        st.info("Failure Analysis functionality coming soon!")
        else:
            st.info("No user stories found in the selected project")

elif ops_agents_enabled and selected_ops == "🎯 Root Cause Analysis":
    st.title("🎯 Root Cause Analysis")
    selected_workspace, selected_project = show_workspace_project_selector()
    
    if selected_workspace and selected_project:
        rca_data = get_project_rca_data(selected_workspace, selected_project)
        
        if rca_data and rca_data["defects"]:
            # Summary metrics
            total_defects = len(rca_data["defects"])
            st.subheader("Root Cause Analysis Overview")
            
            # Display summary metrics with custom container
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                st.metric("Total Defects", total_defects)
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                # Add null checks and default values
                if rca_data["rca_summary"]:
                    top_rca = max(rca_data["rca_summary"].items(), key=lambda x: x[1])
                    display_rca = (top_rca[0][:20] + '...') if len(str(top_rca[0])) > 20 else top_rca[0]
                    percentage = f"{(top_rca[1]/total_defects*100):.1f}%"
                    
                    st.metric(
                        "Most Common Root Cause", 
                        display_rca,
                        percentage
                    )
                    # If truncated, show full name in tooltip
                    if len(str(top_rca[0])) > 20:
                        st.caption(f"Full name: {top_rca[0]}")
                else:
                    st.metric("Most Common Root Cause", "No data", "0%")
                st.markdown('</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                if rca_data["monthly_trend"]:
                    recent_month = max(rca_data["monthly_trend"].keys())
                    recent_count = sum(rca_data["monthly_trend"][recent_month].values())
                    st.metric(
                        "Recent Month Defects",
                        recent_count,
                        f"in {recent_month}"
                    )
                else:
                    st.metric("Recent Month Defects", 0, "No data")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Root Cause Distribution
            st.subheader("Root Cause Distribution")
            
            # Create pie chart for RCA distribution
            fig_pie = px.pie(
                values=list(rca_data["rca_summary"].values()),
                names=list(rca_data["rca_summary"].keys()),
                title="Root Cause Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Monthly Trend
            st.subheader("Root Cause Trend Analysis")
            
            # Create monthly trend data
            months = sorted(rca_data["monthly_trend"].keys())
            root_causes = sorted(set(rca_data["rca_summary"].keys()))
            
            trend_data = []
            for month in months:
                for rc in root_causes:
                    trend_data.append({
                        'Month': month,
                        'Root Cause': rc,
                        'Count': rca_data["monthly_trend"][month].get(rc, 0)
                    })
            
            df_trend = pd.DataFrame(trend_data)
            
            # Create stacked bar chart for monthly trend
            fig_trend = px.bar(
                df_trend,
                x='Month',
                y='Count',
                color='Root Cause',
                title='Monthly Root Cause Trend',
                barmode='stack'
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Severity and Priority Analysis
            st.subheader("Defect Classification Analysis")
            col1, col2 = st.columns(2)
            
            with col1:
                # Severity distribution
                fig_severity = px.pie(
                    values=list(rca_data["severity_distribution"].values()),
                    names=list(rca_data["severity_distribution"].keys()),
                    title="Severity Distribution",
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                st.plotly_chart(fig_severity, use_container_width=True)
            
            with col2:
                # Priority distribution
                fig_priority = px.pie(
                    values=list(rca_data["priority_distribution"].values()),
                    names=list(rca_data["priority_distribution"].keys()),
                    title="Priority Distribution",
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                st.plotly_chart(fig_priority, use_container_width=True)
            
            # Detailed RCA Table
            st.subheader("Detailed Root Cause Analysis")
            df_defects = pd.DataFrame(rca_data["defects"])
            st.dataframe(
                df_defects.style.apply(lambda x: [
                    'background-color: #ffebee' if v == 'High' 
                    else 'background-color: #fff3e0' if v == 'Medium'
                    else 'background-color: #f1f8e9' if v == 'Low'
                    else '' for v in x
                ], subset=['severity', 'priority']),
                use_container_width=True
            )
            
        else:
            st.info("No defect data available for Root Cause Analysis")

else:
    # Show welcome message when no agent is enabled
    st.title("Welcome to SDLC Agent Orchestrator")
    st.info("Please enable either Task Agents or Operation Agents to begin.")