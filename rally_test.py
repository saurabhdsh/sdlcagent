import requests
import json
from typing import Dict, Any, List
import urllib3
import warnings
import plotly.graph_objects as go
from collections import defaultdict
from datetime import datetime
import pygwalker as pyg
import pandas as pd
import plotly.express as px

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Hard-coded Rally configuration
RALLY_ENDPOINT = "https://rally1.rallydev.com/slm/webservice/v2.0"
RALLY_API_KEY = "_abc123"  # Replace with your actual Rally API key

def get_workspaces():
    """Fetch and display available workspaces"""
    headers = {
        "zsessionid": RALLY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"  # Added Accept header
    }
    
    try:
        response = requests.get(
            f"{RALLY_ENDPOINT}/workspace",
            headers=headers,
            params={"fetch": "Name,ObjectID"},
            verify=False
        )
        
        print(f"Response Status: {response.status_code}")  # Debug line
        print(f"Response Content: {response.text[:200]}")  # Debug line
        
        if response.status_code == 200:
            workspaces = response.json().get('QueryResult', {}).get('Results', [])
            if workspaces:
                print("\nAvailable Workspaces:")
                for workspace in workspaces:
                    print(f"ID: {workspace.get('ObjectID')}, Name: {workspace.get('Name')}")
                return workspaces
            else:
                print("No workspaces found in the response")
        else:
            print(f"Failed to fetch workspaces. Status code: {response.status_code}")
            print(f"Response: {response.text}")
        return None
    except Exception as e:
        print(f"Error fetching workspaces: {str(e)}")
        return None

def get_projects(workspace_id: str):
    """Fetch and display projects for a workspace"""
    headers = {
        "zsessionid": RALLY_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{RALLY_ENDPOINT}/project",
        headers=headers,
        params={
            "workspace": f"/workspace/{workspace_id}",
            "fetch": "Name,ObjectID",
            "pagesize": 100
        },
        verify=False
    )
    
    if response.status_code == 200:
        projects = response.json().get('QueryResult', {}).get('Results', [])
        print("\nAvailable Projects:")
        for project in projects:
            print(f"ID: {project.get('ObjectID')}, Name: {project.get('Name')}")
        return projects
    return None

def get_user_stories(workspace_id: str, project_id: str):
    """Fetch and display user stories for a project"""
    headers = {
        "zsessionid": RALLY_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{RALLY_ENDPOINT}/hierarchicalrequirement",
        headers=headers,
        params={
            "workspace": f"/workspace/{workspace_id}",
            "project": f"/project/{project_id}",
            "fetch": "FormattedID,Name",
            "pagesize": 100,
            "order": "CreationDate DESC"
        },
        verify=False
    )
    
    if response.status_code == 200:
        stories = response.json().get('QueryResult', {}).get('Results', [])
        print("\nAvailable User Stories:")
        for story in stories:
            print(f"ID: {story.get('FormattedID')}, Name: {story.get('Name')}")
        return stories
    return None

def get_test_case_details(workspace_id: str, test_case_id: str) -> Dict[str, Any]:
    """Fetch detailed results for a specific test case"""
    headers = {
        "zsessionid": RALLY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # First verify the test case exists
        test_case_params = {
            "workspace": f"/workspace/{workspace_id}",
            "query": f"(FormattedID = {test_case_id})",
            "fetch": "ObjectID,FormattedID,Name"
        }
        
        test_case_response = requests.get(
            f"{RALLY_ENDPOINT}/testcase",
            headers=headers,
            params=test_case_params,
            verify=False
        )
        
        if test_case_response.status_code != 200:
            print(f"Error fetching test case: {test_case_response.status_code}")
            return None
            
        test_case_data = test_case_response.json()
        if not test_case_data.get('QueryResult', {}).get('Results'):
            print(f"Test case {test_case_id} not found")
            return None
            
        test_case_oid = test_case_data['QueryResult']['Results'][0]['ObjectID']
        
        # Now fetch test case results with all required fields
        results_params = {
            "workspace": f"/workspace/{workspace_id}",
            "query": f"(TestCase.ObjectID = {test_case_oid})",
            "fetch": "Build,Date,Verdict,TestCase,WorkProduct,Tester",
            "pagesize": 100,
            "order": "Date DESC"
        }
        
        response = requests.get(
            f"{RALLY_ENDPOINT}/testcaseresult",
            headers=headers,
            params=results_params,
            verify=False
        )
        
        if response.status_code == 200:
            results = response.json().get('QueryResult', {}).get('Results', [])
            
            test_case_history = {
                "test_case_id": test_case_id,
                "results": []
            }
            
            for result in results:
                result_data = {
                    "build": result.get('Build', 'N/A'),
                    "date": result.get('Date', 'N/A'),
                    "verdict": result.get('Verdict', 'N/A'),
                    "work_product": (result.get('WorkProduct', {}) or {}).get('_refObjectName', 'N/A'),
                    "tester": (result.get('Tester', {}) or {}).get('_refObjectName', 'N/A')
                }
                test_case_history["results"].append(result_data)
            
            if not test_case_history["results"]:
                print(f"No test results found for {test_case_id}")
            
            return test_case_history
            
    except Exception as e:
        print(f"Error fetching test case details: {str(e)}")
        print(f"Full error details: {e.__class__.__name__}")
        return None

def plot_test_failure_trend(test_cases_results: List[Dict]) -> None:
    """Plot test case failures by date"""
    # Initialize data structure for failures by date
    failures_by_date = defaultdict(lambda: {"total": 0, "failed": 0})
    
    # Process test case results
    for result in test_cases_results:
        date_str = result.get('date', 'N/A')
        if date_str != 'N/A':
            try:
                # Convert to date only string (YYYY-MM-DD)
                date = date_str.split('T')[0] if 'T' in date_str else date_str
                failures_by_date[date]["total"] += 1
                if result.get('verdict') == 'Fail':
                    failures_by_date[date]["failed"] += 1
            except Exception as e:
                print(f"Error processing date {date_str}: {str(e)}")
    
    if failures_by_date:
        # Sort dates
        dates = sorted(failures_by_date.keys())
        total_tests = [failures_by_date[date]["total"] for date in dates]
        failed_tests = [failures_by_date[date]["failed"] for date in dates]
        
        # Create the figure
        fig = go.Figure()
        
        # Add total tests line
        fig.add_trace(go.Scatter(
            x=dates,
            y=total_tests,
            name="Total Tests",
            line=dict(color="#4CAF50", width=2),
            mode='lines+markers'
        ))
        
        # Add failed tests line
        fig.add_trace(go.Scatter(
            x=dates,
            y=failed_tests,
            name="Failed Tests",
            line=dict(color="#FF6B6B", width=2),
            mode='lines+markers'
        ))
        
        # Update layout
        fig.update_layout(
            title="Test Case Execution Trend",
            xaxis_title="Date",
            yaxis_title="Number of Tests",
            hovermode='x unified',
            showlegend=True,
            plot_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Update axes
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        
        # Show the plot
        fig.show()
    else:
        print("No trend data available")

def plot_test_case_status(test_cases_results: List[Dict]) -> None:
    """Plot test case status by name using Plotly"""
    # Create DataFrame for test case status
    status_data = []
    
    # Process results to get latest status for each test case
    test_case_latest = {}
    for result in test_cases_results:
        test_case = result.get('test_case_id', 'Unknown')
        test_case_name = result.get('test_case_name', test_case)  # Get test case name
        date = result.get('date', 'N/A')
        verdict = result.get('verdict', 'No Run')
        
        # Only update if this is a newer result
        if test_case not in test_case_latest or date > test_case_latest[test_case]['date']:
            test_case_latest[test_case] = {
                'date': date,
                'status': verdict,
                'name': test_case_name,
                'build': result.get('build', 'N/A')
            }
    
    # Convert to list for DataFrame
    for test_case, data in test_case_latest.items():
        status_data.append({
            'Test Case': data['name'],  # Use test case name instead of ID
            'Status': data['status'],
            'Build': data['build'],
            'Date': data['date'].split('T')[0] if 'T' in data['date'] else data['date']
        })
    
    if status_data:
        df = pd.DataFrame(status_data)
        
        # Create a bar chart
        fig = go.Figure()
        
        # Calculate status counts for each test case
        test_cases = df['Test Case'].unique()
        statuses = ['Pass', 'Fail', 'No Run']
        
        for status in statuses:
            counts = []
            for tc in test_cases:
                count = len(df[(df['Test Case'] == tc) & (df['Status'] == status)])
                counts.append(count)
            
            fig.add_trace(go.Bar(
                name=status,
                x=test_cases,
                y=counts,
                marker_color='#4CAF50' if status == 'Pass' else '#FF6B6B' if status == 'Fail' else '#FFB74D'
            ))
        
        # Update layout
        fig.update_layout(
            title='Test Case Status Distribution',
            xaxis_title='Test Cases',
            yaxis_title='Count',
            barmode='stack',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='white',
            height=500
        )
        
        # Update axes
        fig.update_xaxes(
            tickangle=45,
            showgrid=True,
            gridwidth=1,
            gridcolor='LightGray'
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='LightGray'
        )
        
        # Add hover template
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>" +
                         "Status: %{data.name}<br>" +
                         "Count: %{y}<br>" +
                         "<extra></extra>"
        )
        
        # Show the plot
        fig.show()
    else:
        print("No test case status data available")

def get_test_case_results(workspace_id: str, project_id: str, story_id: str) -> Dict[str, Any]:
    """Fetch test case results for a specific user story"""
    headers = {
        "zsessionid": RALLY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # First get all test cases for the user story
    all_test_cases = []
    start = 1
    page_size = 100
    
    while True:
        test_case_params = {
            "workspace": f"/workspace/{workspace_id}",
            "project": f"/project/{project_id}",
            "query": f"(WorkProduct.FormattedID = {story_id})",
            "fetch": "FormattedID,Name,LastVerdict,LastRun,ObjectID,Method,Priority",
            "pagesize": page_size,
            "start": start,
            "order": "FormattedID ASC"
        }
        
        try:
            test_case_response = requests.get(
                f"{RALLY_ENDPOINT}/testcase",
                headers=headers,
                params=test_case_params,
                verify=False
            )
            
            if test_case_response.status_code == 200:
                result_data = test_case_response.json().get('QueryResult', {})
                page_test_cases = result_data.get('Results', [])
                total_results = result_data.get('TotalResultCount', 0)
                
                if not page_test_cases:
                    break
                    
                all_test_cases.extend(page_test_cases)
                
                if len(all_test_cases) >= total_results:
                    break
                    
                start += page_size
            else:
                print(f"Error fetching data: {test_case_response.status_code}")
                break
                
        except Exception as e:
            print(f"Error fetching test cases: {str(e)}")
            break
    
    # Process each test case and collect results
    all_results = []
    for test_case in all_test_cases:
        test_case_id = test_case.get('FormattedID')
        test_case_name = test_case.get('Name', 'Unnamed Test')  # Get test case name
        if test_case_id:
            tc_details = get_test_case_details(workspace_id, test_case_id)
            if tc_details and tc_details.get("results"):
                # Add test case name to each result
                for result in tc_details["results"]:
                    result['test_case_name'] = test_case_name
                    result['test_case_id'] = test_case_id
                all_results.extend(tc_details["results"])
    
    # Plot both trends
    print("\nGenerating test execution trends...")
    plot_test_failure_trend(all_results)
    plot_test_case_status(all_results)
    
    # Continue with existing test case details display
    print(f"\nTest Cases for User Story {story_id}:")
    print("=" * 100)
    print(f"{'Test Case ID':<15} {'Test Case Name':<50} {'Priority':<10} {'Last Verdict':<10}")
    print("-" * 100)
    
    test_data = {
        "total_tests": len(all_test_cases),
        "test_cases": []
    }
    
    for test_case in all_test_cases:
        test_case_data = {
            "test_case_id": test_case.get('FormattedID', 'N/A'),
            "test_case_name": test_case.get('Name', 'Unnamed Test'),
            "priority": test_case.get('Priority', 'N/A'),
            "last_verdict": test_case.get('LastVerdict', 'No Run'),
            "method": test_case.get('Method', 'Manual')
        }
        test_data["test_cases"].append(test_case_data)
        
        print(f"{test_case_data['test_case_id']:<15} {test_case_data['test_case_name'][:50]:<50} "
              f"{test_case_data['priority']:<10} {test_case_data['last_verdict']:<10}")
    
    # Allow user to select a test case for detailed results
    print("\nEnter a Test Case ID to see detailed results (or press Enter to skip)")
    selected_tc = input("Test Case ID: ")
    
    if selected_tc:
        tc_details = get_test_case_details(workspace_id, selected_tc)
        if tc_details and tc_details["results"]:
            print(f"\nDetailed Results for Test Case {selected_tc}:")
            print("=" * 120)
            print(f"{'Build':<20} {'Date':<25} {'Work Product':<30} {'Verdict':<10} {'Tester':<20}")
            print("-" * 120)
            
            for result in tc_details["results"]:
                print(f"{result['build'][:20]:<20} {result['date'][:25]:<25} "
                      f"{result['work_product'][:30]:<30} {result['verdict']:<10} "
                      f"{result['tester'][:20]:<20}")
            
            test_data["selected_test_case"] = tc_details
    
    return test_data

def main():
    # Fetch workspaces
    workspaces = get_workspaces()
    if not workspaces:
        print("Failed to fetch workspaces")
        return
    
    # Get workspace ID from user
    workspace_id = input("\nEnter Workspace ID: ")
    
    # Fetch and display projects
    projects = get_projects(workspace_id)
    if not projects:
        print("Failed to fetch projects")
        return
    
    # Get project ID from user
    project_id = input("\nEnter Project ID: ")
    
    # Fetch and display user stories
    stories = get_user_stories(workspace_id, project_id)
    if not stories:
        print("Failed to fetch user stories")
        return
    
    # Get user story ID from user
    story_id = input("\nEnter User Story ID (e.g., US1234): ")
    
    # Fetch and display test results
    test_data = get_test_case_results(workspace_id, project_id, story_id)
    
    if not test_data:
        print("Failed to fetch test case results")

if __name__ == "__main__":
    main() 