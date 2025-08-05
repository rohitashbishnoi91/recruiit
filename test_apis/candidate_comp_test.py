import requests
import json

def test_candidate_comparison():
    url = "http://localhost:8010/candidates-compare" 
    
    payload = {
        "candidateIds": [
            "68300ded3d8f3bb5ff636f52",  # KIRAN DESHPANDE
            "68300ded3d8f3bb5ff636f53",  # Tejas G.
            "68300ded3d8f3bb5ff636f66",  # Ansh Chawla
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    try:
        print("🚀 Testing Candidate Comparison API...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("\n" + "="*50)
        
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        
        print(f"\n=== API RESPONSE ===")
        print(f"Status Code: {response.status_code}")
        print("\n" + "="*50 + "\n")
        
        if response.status_code == 200:
            json_response = response.json()
            print("📋 FULL RESPONSE:")
            print(json.dumps(json_response, indent=2))
            
            compared_candidates = json_response.get("comparedCandidates", [])
            metadata = json_response.get("comparison_metadata", {})
            
            print("\n" + "="*50)
            print("📊 COMPARISON SUMMARY:")
            print("="*50)
            print(f"Total Candidates Compared: {metadata.get('total_candidates', 0)}")
            
            for i, candidate in enumerate(compared_candidates, 1):
                print(f"\n{i}. Candidate Id: {candidate.get('candidateId', 'N/A')}")
                print(f"   Name: {candidate.get('Name', 'N/A')}")
                print(f"   Title: {candidate.get('Title', 'N/A')}")
                print(f"   Location: {candidate.get('Location', 'N/A')}")
                
        else:
            print("❌ ERROR:")
            try:
                error_response = response.json()
                print(json.dumps(error_response, indent=2))
            except:
                print(f"Raw error response: {response.text}")
                
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_candidate_comparison()
