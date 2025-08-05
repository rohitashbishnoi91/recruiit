import os
import re
import json
import requests
from typing import Dict
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone

from contact_out.utils.transform_schema import transform_linkedin_to_internal
from contact_out.utils.embedding_utils import generate_embedding, JDEmbeddingRequest


# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.messages import HumanMessage


load_dotenv()
CONTACTOUT_API_TOKEN = os.getenv("CONTACTOUT_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Mapping dictionaries
COMPANY_SIZE_MAP = {
    "startup": "1_50",
    "small": "1_50",
    "mid-size": "51_200",
    "medium": "51_200",
    "midsize": "51_200",
    "large": "201_1000",
    "enterprise": "1000_plus"
}


def map_years_of_experience(text: str) -> str:
    try:
        text = text.lower().replace("+", "").replace("plus", "").strip()
        match = re.search(r"\d+", text)
        if match:
            years = int(match.group())
            if years < 1:
                return "0_1"
            elif years <= 2:
                return "1_2"
            elif years <= 5:
                return "3_5"
            elif years <= 10:
                return "6_10"
            else:
                return "10"
    except Exception as e:
        print(f"⚠️ Failed to map experience: {e}")
    return ""


def normalize_filters(filters: Dict) -> Dict:
    clean = {}
    for k, v in filters.items():
        if v in [None, "", [], {}]:
            continue

        if k == "company_size":
            mapped = COMPANY_SIZE_MAP.get(str(v).lower().strip())
            if mapped:
                clean[k] = [mapped]

        elif k == "years_of_experience":
         if isinstance(v, list):
          cleaned_values = []
        for item in v:
            mapped = map_years_of_experience(str(item))
            if mapped:
                cleaned_values.append(mapped)
        if cleaned_values:
            clean[k] = list(set(cleaned_values))  # remove duplicates
        else:
         mapped = map_years_of_experience(str(v))
        if mapped:
            clean[k] = [mapped]

        elif isinstance(v, list):
            clean[k] = v
        else:
            clean[k] = [v] if k in ["job_title", "company", "location", "industry", "education"] else v
        
    print("🧩 Final normalized filters:", clean)


    return clean


def parse_user_query(user_text: str) -> Dict:
    prompt = f"""
Extract filters for ContactOut People Search API based on the user's input:
\"\"\"{user_text}\"\"\"

Return a JSON object with these keys (only if applicable):
keyword, skills, job_title, company, location, industry, education, company_size, years_of_experience, years_in_current_role.
"""

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        google_api_key=GEMINI_API_KEY,
        temperature=0.3
    )
    response = llm.invoke([HumanMessage(content=prompt)]).content

    try:
        if response.startswith("```json"):
            response = response.split("```json")[1].split("```")[0].strip()
        print("Gemini raw response:", response)
        return json.loads(response)
    except Exception as e:
        print("Failed to parse Gemini response:", e)
        print("Raw response:", response)
        return {}


def search_candidates_via_contactout(filters: Dict) -> list:
    url = "https://api.contactout.com/v1/people/search"
    headers = {
        "Authorization": "basic",
        "token": CONTACTOUT_API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {"page": 1, "reveal_info": True, **filters}
    print("Payload being sent to ContactOut:\n", json.dumps(payload, indent=2))
    print("Final years_of_experience:", filters.get("years_of_experience"))


    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise Exception(f"People Search API Error {resp.status_code}: {resp.text}")

    data = resp.json()
    return list(data.get("profiles", {}).keys())


def enrich_profile(profile_url: str) -> Dict:
    url = "https://api.contactout.com/v1/linkedin/enrich"
    headers = {"Authorization": "basic", "token": CONTACTOUT_API_TOKEN}
    params = {"profile": profile_url}

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    profile = resp.json().get("profile")
    if not profile:
        raise ValueError(f"No profile data for {profile_url}")
    return profile


# def process_candidates(filters: Dict, limit=5, jd_id=None, query=None):
#     profile_urls = search_candidates_via_contactout(filters)
#     print(f"🔎 Found {len(profile_urls)} profiles")

#     if not profile_urls:
#         print("❌ No profiles found.")
#         return

#     client = MongoClient(MONGO_URI)
#     collection = client["external_candidates_testing"]["candidates"]

#     for i, profile_url in enumerate(profile_urls[:limit]):
#         print(f"\n🔗 Fetching Profile {i + 1}: {profile_url}")
#         try:
#             raw = enrich_profile(profile_url)
#             transformed = transform_linkedin_to_internal(raw, jd_id=None, query=None)
#             text = transformed.get("Summary") or transformed.get("Headline") or ""
#             embedding = generate_embedding(JDEmbeddingRequest(jd_text=text))
#             transformed["embedding"] = embedding.embedding
#             transformed["embeddingMetadata"] = {"dimension": embedding.dimension}
#             collection.insert_one(transformed)
#             print("✅ Profile stored in MongoDB")
#         except Exception as e:
#             print(f"⚠️ Skipping {profile_url} due to error:", e)

def process_candidates(filters: Dict, limit=5, jd_id=None, query=None):
    profile_urls = search_candidates_via_contactout(filters)
    print(f"Found {len(profile_urls)} profiles")

    if not profile_urls:
        print("No profiles found.")
        return

    client = MongoClient(MONGO_URI)
    collection = client["external_candidates_testing"]["candidates"]

    try:
        collection.create_index("Profile url", unique=False, background=True)
    except Exception:
        pass  # Index might already exist

    for i, profile_url in enumerate(profile_urls[:limit]):
        print(f"\n🔗 Processing Profile {i + 1}: {profile_url}")
        try:
            # Step 1: Check if profile already exists
            existing_profile = collection.find_one({"Profile url": profile_url})
            
            if existing_profile:
                print(f"Profile exists - updating with new JD context")
                update_existing_profile(collection, existing_profile, jd_id, query, profile_url)
            else:
                print(f"✨ New profile - creating fresh record")
                create_new_profile(collection, profile_url, jd_id, query)
                
        except Exception as e:
            print(f"⚠️ Skipping {profile_url} due to error:", e)


def update_existing_profile(collection, existing_profile, jd_id, query, profile_url):
    """Update existing profile with new JD context - SYNC version"""
    try:
        current_timestamp = datetime.now(timezone.utc)
        
        # Get existing JD IDs
        existing_jd_ids = existing_profile.get("search_context", {}).get("jd_ids", [])
        existing_queries = existing_profile.get("search_context", {}).get("queries", [])
        fetch_count = existing_profile.get("search_context", {}).get("fetch_count", 1)
        
        # Prepare update data
        update_data = {
            "updated_at": current_timestamp,
            "search_context.last_query": query,
            "search_context.fetch_count": fetch_count + 1
        }
        
        # Add new JD ID if not already present
        if jd_id and jd_id not in existing_jd_ids:
            update_data["search_context.jd_ids"] = existing_jd_ids + [jd_id]
        
        # Add new query if not already present
        if query and query not in existing_queries:
            update_data["search_context.queries"] = existing_queries + [query]
        
        # Update the document
        result = collection.update_one(
            {"Profile url": profile_url},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            print(f"Updated existing profile with new JD context")
        else:
            print(f"Profile already has this JD context")
            
    except Exception as e:
        print(f"Failed to update existing profile: {e}")



def create_new_profile(collection, profile_url, jd_id, query):
    """Create new profile record"""
    try:
        # Enrich profile from ContactOut
        raw = enrich_profile(profile_url)
        
        # Transform to internal schema
        transformed = transform_linkedin_to_internal(
            profile=raw, 
            jd_id=jd_id, 
            query=query,
            is_update=False
        )
        
        # Generate embedding
        text = transformed.get("Summary") or transformed.get("Headline") or ""
        embedding = generate_embedding(JDEmbeddingRequest(jd_text=text))
        transformed["embedding"] = embedding.embedding
        transformed["embeddingMetadata"] = {
            "dimension": embedding.dimension,
            "generated_at": datetime.now(timezone.utc)
        }
        
        # Insert new document
        collection.insert_one(transformed)
        print("New profile stored in MongoDB")
        
    except Exception as e:
        print(f"Failed to create new profile: {e}")


if __name__ == "__main__":
    user_text = input("🔍 Describe the candidates you're looking for:\n> ")
    raw_filters = parse_user_query(user_text)
    filters = normalize_filters(raw_filters)
    print("\n🧩 Final Filters Used:", json.dumps(filters, indent=2))
    process_candidates(filters=filters, limit=2)
