import openai
import json
import requests
from typing import Optional, Dict, Any, List, Tuple
import logging
import urllib3
import warnings
from datetime import datetime, timedelta
 
# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
# Configuration dictionary
config: Dict[str, str] = {
    "rally_endpoint": "",
    "rally_api_key": "",
    "openai_api_key": "",
    "selected_workspace": "",
    "selected_project": ""
}
 
def call_openai_api(prompt: str, api_key: str, model: str = "gpt-4") -> str:
    """Call OpenAI API with the given prompt and model"""
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=model,  # Use the passed model parameter
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {str(e)}")
        return f"Error: {str(e)}"
 
def check_rally_config() -> bool:
    """
    Check if Rally configuration is properly set up.
   
    Returns:
        bool: True if both rally_endpoint and rally_api_key are set, False otherwise
    """
    return bool(config.get("rally_endpoint")) and bool(config.get("rally_api_key"))
 
def upload_user_story_to_rally(user_story: str, project_id: str) -> Optional[str]:
    """
    Upload a user story to Rally.
    """
    try:
        base_endpoint = config['rally_endpoint'].rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
       
        headers = {
            "zsessionid": config['rally_api_key'],
            "Content-Type": "application/json"
        }
       
        # Create a better story name from the first line or first few words
        story_name = user_story.split('\n')[0][:60]  # Use first line, max 60 chars
        if len(story_name) == 60:
            story_name += "..."
       
        payload = {
            "HierarchicalRequirement": {
                "Name": story_name,
                "Description": user_story,
                "Project": f"/project/{project_id}"
            }
        }
       
        response = requests.post(
            f"{base_endpoint}/hierarchicalrequirement/create",
            headers=headers,
            json=payload
        )
       
        if response.status_code == 200:
            response_data = response.json()
            created_story = response_data.get('CreateResult', {}).get('Object', {})
            formatted_id = created_story.get('FormattedID', 'Unknown')
            return f"User story {formatted_id} successfully created"
        else:
            return f"Failed to upload user story. Status code: {response.status_code}"
           
    except Exception as e:
        print(f"Error uploading to Rally: {str(e)}")
        return None
 
def test_rally_connection(endpoint: str, api_key: str) -> Tuple[bool, str]:
    """Test connection to Rally and validate credentials"""
    try:
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "zsessionid": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
       
        base_endpoint = endpoint.rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
       
        response = session.get(f"{base_endpoint}/subscription")
       
        if response.status_code == 200:
            return True, "Successfully connected to Rally"
        else:
            return False, f"Failed to connect. Status code: {response.status_code}"
           
    except Exception as e:
        return False, f"Connection error: {str(e)}"
 
def get_rally_workspaces() -> List[Dict[str, str]]:
    """
    Fetch available workspaces from Rally
    """
    try:
        # Ensure endpoint is properly formatted
        base_endpoint = config['rally_endpoint'].rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
 
        headers = {
            "zsessionid": config['rally_api_key'],
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
       
        response = requests.get(
            f"{base_endpoint}/workspace",
            headers=headers,
            params={"fetch": "Name,ObjectID,Description"},
            verify=True
        )
       
        print(f"Workspace API Response Status: {response.status_code}")
       
        if response.status_code == 200:
            try:
                response_data = response.json()
                workspaces = response_data.get('QueryResult', {}).get('Results', [])
                workspace_list = []
                for workspace in workspaces:
                    # Print workspace data for debugging
                    print(f"Processing workspace data: {workspace}")
                   
                    workspace_id = workspace.get('ObjectID')
                    workspace_name = workspace.get('Name')
                    if workspace_id and workspace_name:
                        workspace_list.append({
                            "id": str(workspace_id),
                            "name": workspace_name
                        })
                print(f"Found workspaces: {workspace_list}")
                return workspace_list
            except json.JSONDecodeError as je:
                print(f"JSON Decode Error: {str(je)}")
                return []
            except Exception as e:
                print(f"Error processing workspaces: {str(e)}")
                print(f"Full workspace data: {workspaces}")
                return []
        return []
           
    except Exception as e:
        print(f"Error fetching workspaces: {str(e)}")
        return []
 
def get_rally_projects(workspace_id: str) -> List[Dict[str, str]]:
    """
    Fetch available projects for a workspace from Rally
    """
    try:
        # Ensure endpoint is properly formatted
        base_endpoint = config['rally_endpoint'].rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
       
        # Remove any hash fragments from the URL
        base_endpoint = base_endpoint.split('#')[0]
       
        headers = {
            "zsessionid": config['rally_api_key'],
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
       
        # First get the workspace details
        workspace_url = f"{base_endpoint}/workspace/{workspace_id}"
        print(f"Fetching workspace details from: {workspace_url}")
       
        workspace_response = requests.get(
            workspace_url,
            headers=headers,
            verify=True
        )
       
        if workspace_response.status_code != 200:
            print(f"Failed to fetch workspace. Status: {workspace_response.status_code}")
            return []
           
        try:
            workspace_data = workspace_response.json()
            workspace_ref = workspace_data.get('Workspace', {}).get('_ref', '')
           
            if not workspace_ref:
                print("No workspace reference found")
                return []
               
            # Now fetch projects using the workspace reference
            query_url = f"{base_endpoint}/project"
            params = {
                "workspace": workspace_ref,
                "fetch": "Name,ObjectID,Description",
                "pagesize": 100
            }
           
            print(f"Querying projects with URL: {query_url}")
            print(f"Query parameters: {params}")
           
            response = requests.get(
                query_url,
                headers=headers,
                params=params,
                verify=True
            )
           
            print(f"Projects API Response Status: {response.status_code}")
            print(f"Full URL called: {response.url}")
           
            if response.status_code == 200:
                response_data = response.json()
                if 'Errors' in response_data.get('QueryResult', {}) and response_data['QueryResult']['Errors']:
                    print(f"API returned errors: {response_data['QueryResult']['Errors']}")
                    return []
               
                projects = response_data.get('QueryResult', {}).get('Results', [])
                project_list = []
                for project in projects:
                    project_id = project.get('ObjectID') or project.get('_ref', '').split('/')[-1]
                    project_name = project.get('Name', 'Unknown Project')
                    project_list.append({
                        "id": project_id,
                        "name": project_name
                    })
                print(f"Found projects: {project_list}")
                return project_list
               
        except json.JSONDecodeError as je:
            print(f"JSON Decode Error: {str(je)}")
            print(f"Response content: {workspace_response.text}")
            return []
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            print(f"Response content: {workspace_response.text}")
            return []
           
    except Exception as e:
        print(f"Error fetching projects: {str(e)}")
        print(f"Full error: {str(e.__class__.__name__)}: {str(e)}")
        return []
 
def get_rally_user_stories(workspace_id: str, project_id: str) -> List[Dict[str, Any]]:
    """Fetch user stories from Rally"""
    try:
        base_endpoint = config['rally_endpoint'].rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
       
        headers = {
            "zsessionid": config['rally_api_key'],
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
       
        params = {
            "workspace": f"/workspace/{workspace_id}",
            "project": f"/project/{project_id}",
            "fetch": "Name,Description,FormattedID,ObjectID,PlanEstimate,Owner,Tags",
            "pagesize": 100,
            "order": "CreationDate DESC"
        }
       
        print(f"Fetching user stories from: {base_endpoint}/hierarchicalrequirement")
        print(f"Query parameters: {params}")
       
        response = requests.get(
            f"{base_endpoint}/hierarchicalrequirement",
            headers=headers,
            params=params,
            verify=False
        )
       
        print(f"User Stories API Response Status: {response.status_code}")
        print(f"Full URL called: {response.url}")
       
        if response.status_code == 200:
            response_data = response.json()
            stories = response_data.get('QueryResult', {}).get('Results', [])
            story_list = []
            for story in stories:
                story_id = story.get('FormattedID', '')
                story_name = story.get('Name', 'Untitled Story')
                story_desc = story.get('Description', '')
               
                # Create a formatted story entry
                story_list.append({
                    "id": story_id,  # Changed to use FormattedID instead of ObjectID
                    "formatted_id": story_id,
                    "name": story_name,
                    "description": story_desc,
                    "display_name": f"{story_id}: {story_name}"
                })
           
            print(f"Found {len(story_list)} user stories")
            return story_list
           
    except Exception as e:
        print(f"Error fetching user stories: {str(e)}")
        return []
 
def get_user_story_test_data(workspace_id: str, project_id: str, story_id: str) -> Dict[str, Any]:
    try:
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "zsessionid": config['rally_api_key'],
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
       
        base_endpoint = config['rally_endpoint'].rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
       
        # Initialize default test data structure
        test_data = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "other": 0,
            "test_cases": [],
            "defects": [],
            "pass_percentage": 0,
            "statistics": {},
            "failure_trend": {},
            "daily_trend": {}
        }
       
        # Fetch all test cases with pagination
        all_test_cases = []
        start = 1
        page_size = 200
       
        while True:
            test_case_params = {
                "workspace": f"/workspace/{workspace_id}",
                "project": f"/project/{project_id}",
                "query": f"(WorkProduct.FormattedID = \"{story_id}\")",
                "fetch": ("FormattedID,Name,LastVerdict,LastRun,ObjectID,Type,Duration,Method," +
                        "Priority,Owner,TestCaseStatus,LastBuild,LastResult,Results," +
                        "LastRun,LastResultDate,LastUpdateDate"),
                "pagesize": page_size,
                "start": start,
                "order": "FormattedID ASC"
            }
           
            print(f"Fetching test cases for story {story_id}")
            print(f"Query parameters: {test_case_params}")
           
            test_case_response = session.get(
                f"{base_endpoint}/testcase",
                params=test_case_params
            )
           
            if test_case_response.status_code == 200:
                result_data = test_case_response.json().get('QueryResult', {})
                page_test_cases = result_data.get('Results', [])
                total_results = result_data.get('TotalResultCount', 0)
               
                print(f"Found {len(page_test_cases)} test cases on this page")
                print(f"Total results available: {total_results}")
               
                if not page_test_cases:
                    break
                   
                all_test_cases.extend(page_test_cases)
               
                if len(all_test_cases) >= total_results:
                    break
                   
                start += page_size
            else:
                print(f"Error fetching test cases: {test_case_response.status_code}")
                print(f"Response: {test_case_response.text}")
                break
       
        # Add debug logging
        print(f"Fetching test cases for story {story_id}")
        print(f"Total test cases found: {len(all_test_cases)}")
       
        # Add better error handling for test case fetching
        if not all_test_cases:
            print(f"No test cases found for story {story_id}")
            return test_data
 
        test_data["total_tests"] = len(all_test_cases)
       
        # Process test cases with better error handling
        for test_case in all_test_cases:
            try:
                # Safely get test case data with better error handling
                if not isinstance(test_case, dict):
                    print(f"Invalid test case data format: {test_case}")
                    continue
 
                test_case_id = test_case.get('FormattedID')
                if not test_case_id:
                    print("Missing test case ID, skipping...")
                    continue
 
                print(f"Processing test case: {test_case_id}")
               
                # Get LastVerdict directly from LastResult if available
                last_result = test_case.get('LastResult', {})
                if isinstance(last_result, dict):
                    verdict = last_result.get('Verdict', test_case.get('LastVerdict', 'No Run'))
                else:
                    verdict = test_case.get('LastVerdict', 'No Run')
 
                # Safely get all test case attributes with defaults
                test_case_data = {
                    "test_case_id": test_case_id,
                    "test_case_name": test_case.get('Name', 'Unnamed Test'),
                    "tcr_id": test_case.get('ObjectID', 'N/A'),
                    "date_time": test_case.get('LastRun', 'N/A'),
                    "verdict": verdict,
                    "LastBuild": test_case.get('LastBuild', 'Unknown'),
                    "Duration": test_case.get('Duration', 'N/A'),
                    "Owner": (test_case.get('Owner', {}) or {}).get('_refObjectName', 'Unassigned'),
                    "Results": test_case.get('Results', [])
                }
 
                # Update counters based on verdict
                if verdict == 'Pass':
                    test_data["passed"] += 1
                elif verdict == 'Fail':
                    test_data["failed"] += 1
                    print(f"Found failed test: {test_case_id}")  # Debug logging
                else:
                    test_data["other"] += 1
               
                # Add test case to the list
                test_data["test_cases"].append(test_case_data)
               
            except Exception as e:
                print(f"Error processing test case {test_case.get('FormattedID', 'Unknown')}: {str(e)}")
                print(f"Test case data: {test_case}")
                continue
 
        # Calculate pass percentage safely
        total_tests = len(test_data["test_cases"])
        test_data["total_tests"] = total_tests
        if total_tests > 0:
            test_data["pass_percentage"] = (test_data["passed"] / total_tests) * 100
 
        # Initialize and calculate failure trends with better error handling
        today = datetime.now()
        for i in range(10):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            test_data["failure_trend"][date] = {
                "total": 0,
                "failed": 0,
                "failure_rate": 0,
                "failure_details": []
            }
 
        # Process test results for trend with better error handling
        for test_case in test_data["test_cases"]:
            try:
                date_time = test_case.get("date_time")
                if date_time and date_time != 'N/A':
                    # Handle different date formats
                    try:
                        if 'T' in date_time:
                            date = date_time.split('T')[0]
                        else:
                            # Try to parse the date if it's in a different format
                            parsed_date = datetime.strptime(date_time, '%Y-%m-%d')
                            date = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        print(f"Invalid date format: {date_time}")
                        continue
 
                    if date in test_data["failure_trend"]:
                        test_data["failure_trend"][date]["total"] += 1
                        if test_case["verdict"] == 'Fail':
                            test_data["failure_trend"][date]["failed"] += 1
                            # Add more detailed failure information
                            failure_detail = {
                                "test_case_id": test_case["test_case_id"],
                                "test_case_name": test_case["test_case_name"],
                                "build": test_case.get("LastBuild", "Unknown"),
                                "execution_time": test_case.get("Duration", "N/A"),
                                "owner": test_case.get("Owner", "Unassigned")
                            }
                           
                            # Add to failure details if not already present
                            if failure_detail not in test_data["failure_trend"][date]["failure_details"]:
                                test_data["failure_trend"][date]["failure_details"].append(failure_detail)
                                print(f"Added failure detail for test {test_case['test_case_id']} on {date}")  # Debug logging
 
            except Exception as e:
                print(f"Error processing trend data for test case {test_case.get('test_case_id', 'Unknown')}: {str(e)}")
                continue
 
        # Calculate failure rates safely
        for date in test_data["failure_trend"]:
            try:
                total = test_data["failure_trend"][date]["total"]
                failed = test_data["failure_trend"][date]["failed"]
                if total > 0:
                    test_data["failure_trend"][date]["failure_rate"] = (failed / total) * 100
            except Exception as e:
                print(f"Error calculating failure rate for date {date}: {str(e)}")
                continue
 
        print(f"Final test data summary:")
        print(f"Total Tests: {test_data['total_tests']}")
        print(f"Failed Tests: {test_data['failed']}")
        print(f"Passed Tests: {test_data['passed']}")
        print(f"Other Tests: {test_data['other']}")
        print(f"Failure Details Count: {sum(len(data['failure_details']) for data in test_data['failure_trend'].values())}")
 
        return test_data
 
    except Exception as e:
        logging.error(f"Error fetching test data: {str(e)}")
        return {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "other": 0,
            "test_cases": [],
            "defects": [],
            "pass_percentage": 0,
            "statistics": {},
            "failure_trend": {},
            "daily_trend": {}
        }
 
def get_project_rca_data(workspace_id: str, project_id: str) -> Dict[str, Any]:
    """Fetch defects and their root causes for RCA analysis"""
    try:
        base_endpoint = config['rally_endpoint'].rstrip('/')
        if not base_endpoint.endswith('/slm/webservice/v2.0'):
            base_endpoint = f"{base_endpoint}/slm/webservice/v2.0"
       
        headers = {
            "zsessionid": config['rally_api_key'],
            "Content-Type": "application/json"
        }
       
        # Fetch all defects for the project with RCA information
        defect_query_url = f"{base_endpoint}/defect"
        defect_params = {
            "workspace": f"/workspace/{workspace_id}",
            "query": f"(Project.ObjectID = {project_id})",
            "fetch": "ObjectID,Name,State,Priority,Severity,c_RCARootCauseUS,CreationDate",
            "pagesize": 200,
            "order": "CreationDate DESC"
        }
       
        response = requests.get(
            defect_query_url,
            headers=headers,
            params=defect_params,
            verify=False
        )
       
        if response.status_code == 200:
            defects = response.json().get('QueryResult', {}).get('Results', [])
           
            rca_data = {
                "defects": [],
                "rca_summary": {},
                "monthly_trend": {},
                "severity_distribution": {},
                "priority_distribution": {},
                "state_distribution": {}
            }
           
            for defect in defects:
                creation_date = defect.get('CreationDate', '').split('T')[0]
                root_cause = defect.get('c_RCARootCauseUS', 'Unspecified')
                severity = defect.get('Severity', 'None')
                priority = defect.get('Priority', 'None')
                state = defect.get('State', 'None')
               
                # Add to defects list
                rca_data["defects"].append({
                    "name": defect.get('Name', 'Unnamed Defect'),
                    "root_cause": root_cause,
                    "severity": severity,
                    "priority": priority,
                    "state": state,
                    "creation_date": creation_date
                })
               
                # Update RCA summary
                rca_data["rca_summary"][root_cause] = rca_data["rca_summary"].get(root_cause, 0) + 1
               
                # Update monthly trend
                month = creation_date[:7]  # Get YYYY-MM
                if month not in rca_data["monthly_trend"]:
                    rca_data["monthly_trend"][month] = {}
                rca_data["monthly_trend"][month][root_cause] = \
                    rca_data["monthly_trend"][month].get(root_cause, 0) + 1
               
                # Update distributions
                rca_data["severity_distribution"][severity] = \
                    rca_data["severity_distribution"].get(severity, 0) + 1
                rca_data["priority_distribution"][priority] = \
                    rca_data["priority_distribution"].get(priority, 0) + 1
                rca_data["state_distribution"][state] = \
                    rca_data["state_distribution"].get(state, 0) + 1
           
            return rca_data
           
    except Exception as e:
        logging.error(f"Error fetching RCA data: {str(e)}")
        return None