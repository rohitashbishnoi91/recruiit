import os
import sys
from datetime import datetime, timezone
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def transform_linkedin_to_internal(profile, jd_id, query, is_update=False, existing_jd_ids=None):
    """
    Transform LinkedIn profile with support for updates and multi-JD tracking
    
    Args:
        profile: Raw LinkedIn profile data
        jd_id: Current JD ID that triggered this fetch
        query: Search query used
        is_update: Whether this is updating an existing record
        existing_jd_ids: List of existing JD IDs (for updates)
    """
    education_data = profile.get("education", [])
    experience_data = profile.get("experience", [])

    transformed_education = []
    for edu in education_data:
        transformed_education.append({
            "school": {"name": edu.get("school_name")},
            "fieldOfStudy": edu.get("field_of_study"),
            "degree": edu.get("degree"),
            "startedYear": int(edu["start_date_year"]) if edu.get("start_date_year") else None,
            "endedYear": int(edu["end_date_year"]) if edu.get("end_date_year") else None
        })

    transformed_experience = []
    for exp in experience_data:
        transformed_experience.append({
            "company": {"name": exp.get("company_name")},
            "startDateMonth": exp.get("start_date_month"),
            "startDateYear": exp.get("start_date_year"),
            "endDateMonth": exp.get("end_date_month"),
            "endDateYear": exp.get("end_date_year"),
            "positions": [
                {
                    "title": exp.get("title"),
                    "description": exp.get("summary"),
                    "location": exp.get("locality"),
                    "startDateMonth": exp.get("start_date_month"),
                    "startDateYear": exp.get("start_date_year"),
                    "endDateMonth": exp.get("end_date_month"),
                    "endDateYear": exp.get("end_date_year")
                }
            ]
        })

    current_timestamp = datetime.now(timezone.utc)
    
    # Handle JD IDs as list for multi-JD tracking
    if is_update:
        # For updates, add new jd_id to existing list if not already present
        jd_ids_list = existing_jd_ids or []
        if jd_id and jd_id not in jd_ids_list:
            jd_ids_list.append(jd_id)
    else:
        # For new records, create new list with current jd_id
        jd_ids_list = [jd_id] if jd_id else []

    # Enhanced search context with multiple JD tracking
    search_context = {
        "jd_ids": jd_ids_list,  # Changed from single jd_id to list
        "queries": [query] if not is_update else [],  # Track all queries
        "last_query": query,
        "fetch_count": 1 if not is_update else None  # Track how many times fetched
    }

    final_obj = {
        "Name": profile.get("full_name"),
        "Title": profile.get("headline"),
        "Headline": profile.get("headline"),
        "Summary": profile.get("summary"),
        "Industry": profile.get("industry"),
        "Location": profile.get("location"),
        "Skills": profile.get("skills", []),
        "Certifications": [cert.get("name") for cert in profile.get("certifications", [])],
        "Publications": [pub.get("title") for pub in profile.get("publications", [])],
        "Education": transformed_education,
        "Experience": transformed_experience,
        "Experience in days": None,
        "Profile url": profile.get("url"),
        "embedding": None,
        "embeddingMetadata": {},
        
        # Enhanced timestamp tracking
        "created_at": current_timestamp if not is_update else None,  # Only set on creation
        "updated_at": current_timestamp,  # Always updated
        "search_context": search_context,
    }

    # Remove None values for updates
    if is_update:
        final_obj = {k: v for k, v in final_obj.items() if v is not None}

    return final_obj
