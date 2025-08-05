import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_soft_skills_mappings, get_candidates



def calculate_weighted_soft_skills_score(raw_score, max_points=5):
    """Scale percentile (0-100) to weighted points (0-5)"""
    return (raw_score / 100) * max_points

def extract_soft_skills_from_jd_keywords(jd_data):
    """Extract soft skills from JD keywords"""
    keywords = jd_data.get('keywords', [])
    
    if not keywords:
        return set()
    
    soft_skills_ref, soft_skills_synonyms = get_soft_skills_mappings()
    jd_soft_skills = set()
    
    # Normalize keywords and check against soft skills reference
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        
        # Direct match with soft skills reference
        if keyword_lower in soft_skills_ref:
            jd_soft_skills.add(keyword_lower)
        
        # Check against synonyms
        for skill, synonyms in soft_skills_synonyms.items():
            if keyword_lower in synonyms or keyword_lower == skill:
                jd_soft_skills.add(skill)
    
    return jd_soft_skills

def extract_candidate_soft_skills(candidate):
    """Extract soft skills from candidate's Skills array using reference list"""
    candidate_skills = candidate.get('Skills', [])
    
    if not candidate_skills:
        return set()
    
    soft_skills_ref, soft_skills_synonyms = get_soft_skills_mappings()
    candidate_soft_skills = set()
    
    # Filter candidate skills to only include soft skills
    for skill in candidate_skills:
        skill_lower = skill.lower().strip()
        
        # Direct match with soft skills reference
        if skill_lower in soft_skills_ref:
            candidate_soft_skills.add(skill_lower)
        
        # Check against synonyms
        for soft_skill, synonyms in soft_skills_synonyms.items():
            if skill_lower in synonyms or skill_lower == soft_skill:
                candidate_soft_skills.add(soft_skill)
    
    return candidate_soft_skills

def calculate_soft_skills_raw_score(candidate_soft_skills, jd_soft_skills, soft_skills_synonyms, debug=False):
    """Calculate raw soft skills score (0-100)"""
    
    if not jd_soft_skills:
        return 0.0  # No soft skills required in JD
    
    if not candidate_soft_skills:
        return 0.0  # Candidate has no soft skills
    
    # Exact matches
    exact_matches = candidate_soft_skills.intersection(jd_soft_skills)
    
    # Synonym-based related matches
    related_matches = set()
    for jd_skill in jd_soft_skills - exact_matches:
        jd_synonyms = soft_skills_synonyms.get(jd_skill, set())
        if candidate_soft_skills.intersection(jd_synonyms):
            related_matches.add(jd_skill)
    
    # Total matched skills
    matched_skills = exact_matches.union(related_matches)
    
    if debug:
        print(f"JD Soft Skills: {jd_soft_skills}")
        print(f"Candidate Soft Skills: {candidate_soft_skills}")
        print(f"Exact Matches: {exact_matches}")
        print(f"Related Matches: {related_matches}")
        print(f"Total Matched: {matched_skills}")
    
    # Calculate score
    if len(jd_soft_skills) == 0:
        return 100.0
    
    match_percentage = (len(matched_skills) / len(jd_soft_skills)) * 100
    return match_percentage

def score_soft_skills_component(candidates, jd_data, debug=False):
    """Score soft skills component for all candidates"""
    
    # Extract soft skills requirements from JD
    jd_soft_skills = extract_soft_skills_from_jd_keywords(jd_data)
    soft_skills_ref, soft_skills_synonyms = get_soft_skills_mappings()
    
    if debug:
        print(f"JD Soft Skills Required: {jd_soft_skills}")
        print("-" * 50)
    
    # Step 1: Calculate raw scores
    for candidate in candidates:
        candidate_soft_skills = extract_candidate_soft_skills(candidate)
        raw_score = calculate_soft_skills_raw_score(
            candidate_soft_skills, jd_soft_skills, soft_skills_synonyms, debug=debug
        )
        candidate['raw_soft_skills_score'] = raw_score
        
        if debug:
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Candidate Soft Skills: {candidate_soft_skills}")
            print(f"Raw Score: {raw_score:.1f}")
            print("-" * 30)
    
    # Step 2: Calculate percentiles
    all_raw_scores = [c['raw_soft_skills_score'] for c in candidates]
    
    # Step 3: Calculate weighted scores
    for candidate in candidates:
        raw_score = candidate['raw_soft_skills_score']
        candidate['soft_skills_weighted_score'] = calculate_weighted_soft_skills_score(raw_score, max_points=5)

    if debug:
        print("Soft skills scoring completed!")

    return candidates



def final_soft_skills_score(candidates, jd_data, debug=False):
    """Main function to call for soft skills scoring"""
    
    if debug:
        print(f"Extracted Soft Skills Requirements: {jd_data}")
    
    # Score soft skills component
    scored_candidates = score_soft_skills_component(candidates, jd_data, debug=debug)
    
    return scored_candidates





def main():
    # Test with your JD data including soft skills in keywords
    jd_data = {
            "job_title": "Python Developer",
            "years_of_experience": "2+",
            "keywords": [
                "Python Developer",
                "Python",
                "Flask", 
                "FastAPI",
                "RESTful APIs",
                "API Development",
                "SQL",
                "PostgreSQL",
                "Git",
                "GitHub",
                "DSA",
                "Data Structures and Algorithms",
                "Software Development",
                "Backend Development", 
                "Web Applications",
                "2+ years experience",
                "Software Engineer",
                "API Design",
                "Problem-solving",  # ← Soft skill
                "Teamwork"          # ← Soft skill
            ]
    }
    
    # Get candidates from knowledge base
    candidates = get_candidates()
    
    # Score soft skills component
    scored_candidates = final_soft_skills_score(candidates, jd_data, debug=True)
    
    # Sort by weighted score
    scored_candidates.sort(key=lambda x: x['soft_skills_weighted_score'], reverse=True)
    
    print("\n" + "="*70)
    print("Soft Skills Scores:")
    print("="*70)
    for candidate in scored_candidates[:10]:  # Show top 10
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_soft_skills_score']:.1f}%, "
              f"Weighted: {candidate['soft_skills_weighted_score']:.1f}/5")

# if __name__ == "__main__":
#     main()
