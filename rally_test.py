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
            "fetch": "Build,Date,Verdict,TestCase,WorkProduct,Tester,Notes,Attachments",
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
                    "tester": (result.get('Tester', {}) or {}).get('_refObjectName', 'N/A'),
                    "notes": result.get('Notes', 'N/A')
                }
                test_case_history["results"].append(result_data)
            
            if not test_case_history["results"]:
                print(f"No test results found for {test_case_id}")
            
            return test_case_history
            
    except Exception as e:
        print(f"Error fetching test case details: {str(e)}")
        print(f"Full error details: {e.__class__.__name__}")
        return None

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
    
    # Process and display results
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
                if result['notes'] != 'N/A':
                    print(f"Notes: {result['notes']}\n")
            
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