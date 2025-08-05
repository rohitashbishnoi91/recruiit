from scipy.stats import percentileofscore
import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_candidates, get_locations

CITY_VARIATIONS = get_locations()

# def calculate_percentile_rank(raw_score, all_raw_scores):
#     """Calculate percentile rank using mean for better tie handling"""
#     return percentileofscore(all_raw_scores, raw_score, kind='mean')

def calculate_weighted_location_score(raw_score, max_points=5):
    """Scale percentile (0-100) to weighted points (0-5)"""
    return (raw_score / 100) * max_points

def extract_city_from_jd(jd_data):
    """Extract city from JD job_type_workplace_location (3rd element if present)"""
    job_location = jd_data.get('job_type_workplace_location', '').strip()
    
    if not job_location:
        return None
    
    # Remove work type indicators
    location_clean = job_location.lower()
    work_indicators = [
        'full-time', 'full time', 'part-time', 'part time',
        'on-site', 'onsite', 'contract', 'permanent', 'temporary'
    ]
    
    for indicator in work_indicators:
        location_clean = location_clean.replace(indicator, '')
    
    # Clean up extra commas and spaces
    location_clean = location_clean.strip(', ').strip()
    
    # Parse location parts
    if location_clean:
        location_parts = [part.strip().lower() for part in location_clean.split(',')]
        location_parts = [part for part in location_parts if part]  # Remove empty parts
        
        # Return 3rd element if present (index 2), otherwise None
        if len(location_parts) >= 3:
            return location_parts[2]  # 3rd element
        elif len(location_parts) == 1:
            return location_parts[0]  # If only one element, assume it's city
    
    return None

def extract_city_from_candidate(candidate):
    """Extract city from candidate location (1st element typically)"""
    candidate_location = candidate.get('Location', '').strip()
    
    if not candidate_location:
        return None
    
    # Parse candidate location: "Bengaluru, Karnataka, India"
    location_parts = [part.strip().lower() for part in candidate_location.split(',')]
    location_parts = [part for part in location_parts if part]
    
    # Return 1st element (city) if present
    if len(location_parts) > 0:
        return location_parts[0]
    
    return None

def normalize_city_name(city):
    """Normalize city names using variations list"""
    if not city:
        return None
        
    city = city.lower().strip()
    
    # Check if city is in variations mapping
    if city in CITY_VARIATIONS:
        # Return the first variation (canonical name)
        return list(CITY_VARIATIONS[city])[0]
    
    # Check if city is a variation of any mapped city
    for canonical_city, variations in CITY_VARIATIONS.items():
        if city in variations:
            return canonical_city
    
    return city  # Return as-is if no mapping found

def calculate_location_fit_score(jd_city, candidate_city):
    """Calculate location fit score - simple city matching only"""
    
    # If JD has no city, score is 0
    if not jd_city:
        return 0
    
    # If candidate has no city, score is 0
    if not candidate_city:
        return 0
    
    # Normalize both cities
    jd_city_normalized = normalize_city_name(jd_city)
    candidate_city_normalized = normalize_city_name(candidate_city)
    
    # Simple match: 100 for exact match, 0 for no match
    if jd_city_normalized == candidate_city_normalized:
        return 100
    
    # Check if cities are variations of each other
    if jd_city_normalized in CITY_VARIATIONS and candidate_city_normalized in CITY_VARIATIONS[jd_city_normalized]:
        return 100
    if candidate_city_normalized in CITY_VARIATIONS and jd_city_normalized in CITY_VARIATIONS[candidate_city_normalized]:
        return 100
    
    return 0  # No match

def calculate_location_raw_score(candidate, jd_data, debug=False):
    """Calculate raw location fit score (0-100)"""
    
    # Extract cities
    jd_city = extract_city_from_jd(jd_data)
    candidate_city = extract_city_from_candidate(candidate)
    
    # Calculate fit score
    fit_score = calculate_location_fit_score(jd_city, candidate_city)
    
    if debug:
        job_location_str = jd_data.get('job_type_workplace_location', '')
        candidate_location_str = candidate.get('Location', '')
        print(f"JD Location: '{job_location_str}' -> City: '{jd_city}'")
        print(f"Candidate Location: '{candidate_location_str}' -> City: '{candidate_city}'")
        print(f"Location Fit Score: {fit_score}")
        print("-" * 50)
    
    return fit_score

def score_location_component(candidates, jd_data, debug=False):
    """Score location fit component for all candidates"""
    
    if debug:
        job_location = jd_data.get('job_type_workplace_location', '')
        jd_city = extract_city_from_jd(jd_data)
        print(f"JD Location: '{job_location}' -> Extracted City: '{jd_city}'")
        print("-" * 50)
    
    # Step 1: Calculate raw scores
    for candidate in candidates:
        raw_score = calculate_location_raw_score(candidate, jd_data, debug=debug)
        candidate['raw_location_score'] = raw_score
        
        if debug:
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Location: {candidate.get('Location', '')}")
            print(f"Raw Score: {raw_score:.1f}")
            print("-" * 30)
    
    # Step 2: Calculate percentiles
    all_raw_scores = [c['raw_location_score'] for c in candidates]
    
    # Step 3: Calculate weighted scores
    for candidate in candidates:
        raw_score = candidate['raw_location_score']
        candidate['location_weighted_score'] = calculate_weighted_location_score(raw_score, max_points=5)

    if debug:
        print("Location scoring completed!")

    return candidates



def final_location_score(candidates, jd_data, debug=False):
    """Main function to call for location scoring"""
    
    if debug:
        print(f"Extracted Location Requirements: {jd_data}")
    
    # Score location component
    scored_candidates = score_location_component(candidates, jd_data, debug=debug)
    
    return scored_candidates



def main():
    # Single JD test with Delhi city
    jd_data = {
            "job_type_workplace_location": "Full-time, On-site, Bangalore"
    }
    
    # Get candidates from knowledge base
    candidates = get_candidates()
    
    # Score location component
    scored_candidates = final_location_score(candidates, jd_data, debug=True)
    
    # Sort by weighted score
    scored_candidates.sort(key=lambda x: x['location_weighted_score'], reverse=True)
    
    print("\n" + "="*70)
    print("Location Fit Scores:")
    print("="*70)
    for candidate in scored_candidates[:10]:  # Show top 10
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_location_score']:.1f}%, "
              f"Weighted: {candidate['location_weighted_score']:.1f}/5")

# if __name__ == "__main__":
#     main()
