import requests
import json
from typing import Dict, Any
import urllib3
import warnings

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

def get_test_case_results(workspace_id: str, project_id: str, story_id: str) -> Dict[str, Any]:
    """Fetch test case results for a specific user story"""
    headers = {
        "zsessionid": RALLY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    all_test_cases = []
    start = 1
    page_size = 100
    
    while True:
        # First fetch test cases for the user story with pagination
        test_case_params = {
            "workspace": f"/workspace/{workspace_id}",
            "project": f"/project/{project_id}",
            "query": f"(WorkProduct.FormattedID = {story_id})",
            "fetch": "FormattedID,Name,LastVerdict,LastRun,ObjectID",
            "pagesize": page_size,
            "start": start,
            "order": "FormattedID ASC"
        }
        
        try:
            # Get test cases for current page
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
    
    # Process and display results
    print(f"\nTest Results for User Story {story_id}:")
    print("=" * 100)
    print(f"{'Test Case ID':<15} {'Test Case Name':<30} {'TCR ID':<15} {'Verdict':<10} {'Date and Time'}")
    print("-" * 100)
    
    test_data = {
        "total_tests": len(all_test_cases),
        "passed": 0,
        "failed": 0,
        "results": []
    }
    
    # Now get the latest test case results for each test case
    for test_case in all_test_cases:
        test_case_id = test_case.get('FormattedID')
        test_case_name = test_case.get('Name', 'Unnamed Test')
        verdict = test_case.get('LastVerdict', 'No Run')
        
        # Get the latest test case result
        tcr_params = {
            "workspace": f"/workspace/{workspace_id}",
            "query": f"(TestCase.FormattedID = {test_case_id})",
            "fetch": "ObjectID,Date,Verdict",
            "pagesize": 1,
            "order": "Date DESC"
        }
        
        tcr_response = requests.get(
            f"{RALLY_ENDPOINT}/testcaseresult",
            headers=headers,
            params=tcr_params,
            verify=False
        )
        
        tcr_id = 'N/A'
        date_time = 'N/A'
        
        if tcr_response.status_code == 200:
            tcr_results = tcr_response.json().get('QueryResult', {}).get('Results', [])
            if tcr_results:
                latest_result = tcr_results[0]
                tcr_id = latest_result.get('ObjectID', 'N/A')
                date_time = latest_result.get('Date', 'N/A')
                verdict = latest_result.get('Verdict', verdict)
        
        if verdict == 'Pass':
            test_data["passed"] += 1
        elif verdict == 'Fail':
            test_data["failed"] += 1
        
        # Store result details
        result_data = {
            "test_case_id": test_case_id,
            "test_case_name": test_case_name,
            "tcr_id": tcr_id,
            "verdict": verdict,
            "date_time": date_time
        }
        test_data["results"].append(result_data)
        
        # Print result details
        print(f"{result_data['test_case_id']:<15} {result_data['test_case_name'][:30]:<30} "
              f"{result_data['tcr_id']:<15} {result_data['verdict']:<10} {result_data['date_time']}")
    
    # Print summary
    print("\nSummary:")
    print(f"Total Test Cases: {test_data['total_tests']}")
    print(f"Passed: {test_data['passed']}")
    print(f"Failed: {test_data['failed']}")
    
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