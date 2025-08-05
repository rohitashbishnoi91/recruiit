from scipy.stats import percentileofscore
import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_job_title_mappings, get_candidates


def calculate_weighted_title_score(raw_score, max_points=10):
    """Convert raw score (0-100) directly to weighted points (0-10)"""
    return (raw_score / 100) * max_points

def extract_job_title_from_jd(jd_data):
    """Extract job title from JD structure"""
    return jd_data.get('full_description', {}).get('job_title', '').strip()

def normalize_job_title_rule_based(title):
    """Normalize job title using rule-based approach (KEEP seniority for separate scoring)"""
    if not title:
        return ""
    
    # Get normalization mappings from knowledge base
    normalization_mappings, similarity_groups = get_job_title_mappings()
    
    # Convert to lowercase
    title = title.lower().strip()
    
    # Remove work arrangement indicators only
    for indicator in normalization_mappings['work_indicators']:
        title = re.sub(rf'\b{re.escape(indicator)}\b', '', title)
    
    # Remove company-specific terms only
    for term in normalization_mappings['company_terms']:
        title = re.sub(rf'\b{re.escape(term)}\b', '', title)
    
    # Handle combined roles (take primary role)
    separators = [' / ', '/', ' | ', '|', ' & ', '&', ' - ', '-']
    for sep in separators:
        if sep in title:
            roles = [role.strip() for role in title.split(sep)]
            title = roles[0] if roles else title
            break
    
    # Remove parenthetical content
    title = re.sub(r'\([^)]*\)', '', title)
    
    # Clean whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title

def calculate_role_group_similarity_fast(jd_title, candidate_title):
    """Fast rule-based similarity using precise role groups"""
    normalization_mappings, similarity_groups = get_job_title_mappings()
    
    jd_normalized = normalize_job_title_rule_based(jd_title)
    candidate_normalized = normalize_job_title_rule_based(candidate_title)
    
    # Find which groups each title belongs to using EXACT phrase matching
    jd_groups = set()
    candidate_groups = set()
    
    for group_name, roles in similarity_groups.items():
        for role in roles:
            # Exact phrase matching - not substring
            if role == jd_normalized or jd_normalized.endswith(f" {role}") or jd_normalized.startswith(f"{role} "):
                jd_groups.add(group_name)
            if role == candidate_normalized or candidate_normalized.endswith(f" {role}") or candidate_normalized.startswith(f"{role} "):
                candidate_groups.add(group_name)
    
    # Calculate group overlap
    if jd_groups and candidate_groups:
        overlap = jd_groups.intersection(candidate_groups)
        if overlap:
            # Perfect group match
            return 100.0
        else:
            # Check for related groups
            related_score = calculate_related_group_score(jd_groups, candidate_groups)
            return related_score
    
    # Fallback: direct string similarity
    return calculate_simple_string_similarity(jd_normalized, candidate_normalized)

def calculate_related_group_score(jd_groups, candidate_groups):
    """Calculate similarity between related role groups"""
    
    # Define related groups with similarity scores
    related_groups = {
        "python_development": {"software_development": 85, "backend_development": 80, "data_science": 60},
        "software_development": {"backend_development": 80, "frontend_development": 80, "python_development": 85},
        "backend_development": {"software_development": 80, "python_development": 80, "devops_sre": 60},
        "frontend_development": {"software_development": 80, "mobile_development": 60, "design": 40},
        "data_science": {"machine_learning": 70, "python_development": 60, "research": 60},
        "machine_learning": {"data_science": 70, "research": 60, "software_development": 50},
        "devops_sre": {"backend_development": 60, "software_development": 50},
        "product_management": {"consulting": 40, "technical_leadership": 30},
        "quality_assurance": {"software_development": 40, "backend_development": 50},
        "mobile_development": {"software_development": 70, "frontend_development": 60}
    }
    
    max_related_score = 0
    for jd_group in jd_groups:
        for candidate_group in candidate_groups:
            if jd_group in related_groups and candidate_group in related_groups[jd_group]:
                max_related_score = max(max_related_score, related_groups[jd_group][candidate_group])
            elif candidate_group in related_groups and jd_group in related_groups[candidate_group]:
                max_related_score = max(max_related_score, related_groups[candidate_group][jd_group])
    
    return max_related_score

def calculate_simple_string_similarity(title1, title2):
    """Simple rule-based string similarity"""
    if not title1 or not title2:
        return 0.0
    
    # Exact match
    if title1 == title2:
        return 100.0
    
    # Split into words
    words1 = set(title1.split())
    words2 = set(title2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate word overlap
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    # Jaccard similarity
    jaccard = len(intersection) / len(union) if union else 0
    
    # Boost score for key technical words
    key_words = {"python", "java", "javascript", "react", "angular", "data", "ml", "ai"}
    key_matches = intersection.intersection(key_words)
    if key_matches:
        jaccard += 0.3  # Boost for matching technology words
    
    return min(100.0, jaccard * 100)

def calculate_title_similarity_raw_score_rule_based(candidate_title, jd_title, debug=False):
    """Calculate raw job title similarity score using ONLY rule-based approach"""
    if not candidate_title or not jd_title:
        return 0.0
    
    # Use fast rule-based similarity
    similarity_score = calculate_role_group_similarity_fast(jd_title, candidate_title)
    
    if debug:
        print(f"JD Title: '{jd_title}' -> Normalized: '{normalize_job_title_rule_based(jd_title)}'")
        print(f"Candidate Title: '{candidate_title}' -> Normalized: '{normalize_job_title_rule_based(candidate_title)}'")
        print(f"Rule-based Similarity Score: {similarity_score:.1f}")
        print("-" * 50)
    
    return similarity_score

def score_title_component_rule_based(candidates, jd_title, debug=False):
    """Score job title similarity component using ONLY rule-based approach"""
    
    if debug:
        print(f"JD Job Title: {jd_title}")
        print("-" * 50)
    
    # Step 1: Calculate raw scores using rule-based approach
    for candidate in candidates:
        candidate_title = candidate.get('Title', '')
        raw_score = calculate_title_similarity_raw_score_rule_based(
            candidate_title, jd_title, debug=debug
        )
        candidate['raw_title_score'] = raw_score
        
        if debug:
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Title: {candidate_title}")
            print(f"Raw Score: {raw_score:.1f}")
            print("-" * 30)
    
    # Step 2: Calculate percentiles
    all_raw_scores = [c['raw_title_score'] for c in candidates]
    
    # Step 3: Calculate weighted scores
    for candidate in candidates:
        raw_score = candidate['raw_title_score']
        candidate['title_weighted_score'] = calculate_weighted_title_score(
            raw_score, max_points=10
        )

    if debug:
        print("Job title scoring completed!")

    return candidates


def final_title_score(candidates, jd_data, debug=False):
    """Main function to call for job title scoring"""
    
    jd_title = extract_job_title_from_jd(jd_data)
    
    if debug:
        print(f"Extracted JD Title: {jd_title}")
    
    scored_candidates = score_title_component_rule_based(candidates, jd_title, debug=debug)
    
    return scored_candidates

def main():
    # Test with your JD data
    jd_data = {
        "full_description": {
            "job_title": "Python Developer",
            "years_of_experience": "2+",
            "qualifications": [
                "Bachelor's degree in Computer Science, Software Engineering, or a related field."
            ]
        }
    }
    
    # Get candidates from knowledge base
    candidates = get_candidates()
    
    # Score title component using rule-based approach
    scored_candidates = final_title_score(candidates, jd_data, debug=True)
    
    # Sort by weighted score
    scored_candidates.sort(key=lambda x: x['title_weighted_score'], reverse=True)
    
    print("\n" + "="*70)
    print("Rule-Based Job Title Similarity Scores:")
    print("="*70)
    for candidate in scored_candidates:
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_title_score']:.1f}%, "
              f"Weighted: {candidate['title_weighted_score']:.1f}/10")

if __name__ == "__main__":
    main()
