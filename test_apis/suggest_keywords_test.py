import requests
import json

def test_job_description_generator():
    url= "http://20.193.128.47:8010/suggest-keywords"
    # url = "http://localhost:8010/suggest-keywords"
    
    payload = {
        # "prompt": "Frontend Developer, 5 years experience, UI/UX design"
        "user_input": "AI/ML Expert, 2 years experience, Python",
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        
        print("\n=== API RESPONSE ===\n")
        
        # Pretty print the JSON response
        if response.status_code == 200:
            json_response = response.json()
            print(json.dumps(json_response, indent=2))
        else:
            print(f"Error response: {response.text}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_job_description_generator()