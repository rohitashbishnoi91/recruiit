from scipy.stats import percentileofscore
import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bson import ObjectId
from knowledge_base import get_related_skills, get_candidates

# Regex to extract skills from JD requirements
def extract_skills_from_requirements(skills_required):
    all_skills = []
    
    pattern = r'(?<=:\s)(.*)'
    
    for requirement in skills_required:
        match = re.search(pattern, requirement)
        if match:
            skills_text = match.group(1).strip()
            
            skills = [skill.strip() for skill in skills_text.split(',')]
            all_skills.extend(skills)
    
    return all_skills



def calculate_percentile_rank(raw_score, all_raw_scores):
    return percentileofscore(all_raw_scores, raw_score, kind='mean')  #strict, mean


def calculate_weighted_skills_score(raw_score, max_points=35):
    return (raw_score / 100) * max_points



def calculate_skills_raw_score(candidate_skills, jd_skills, related_skills_map):
    
    # Exact matches
    exact_matches = candidate_skills.intersection(jd_skills)
    # print(f"Exact Matches: {exact_matches}")
    
    # Ontology-based related matches
    related_matches = set()
    for skill in jd_skills - exact_matches:
        synonyms = related_skills_map.get(skill, set())
        if candidate_skills.intersection(synonyms):
            related_matches.add(skill)
    
    # print(f"Related Matches: {related_matches}")

    matched = exact_matches.union(related_matches)
    
    if not jd_skills:
        return 100.0  # No requirements - full score
    
    return (len(matched) / len(jd_skills)) * 100




def score_skills_component(candidates, jd_skills, related_skills_map, debug=False):

    jd_set = {s.lower().strip() for s in jd_skills}     # Normalize JD skills

    if debug:
        print(f"JD Skills (normalized): {jd_set}")
        print("-" * 50)
    
    # Step 1: Compute raw scores
    for cand in candidates:
        cand_set = {s.lower().strip() for s in cand.get('Skills', [])}
        cand['raw_skill_score'] = calculate_skills_raw_score(cand_set, jd_set, related_skills_map)
    
    # Collect all raw scores
    all_raw = [c['raw_skill_score'] for c in candidates]
    
    # Step 2 & 3: Compute percentile and weighted scores
    for cand in candidates:
        raw_score = cand['raw_skill_score']
        cand['skill_weighted_score'] = calculate_weighted_skills_score(raw_score, max_points=35)
        # Remove percentile calculation completely

    if debug:
        print("Skills scoring completed!")

    return candidates



######################## MAIN FUNCTION TO CALL ########################

def final_skills_score(candidates, jd_skills_req, debug=False):
    extracted_jd_skills = extract_skills_from_requirements(jd_skills_req)

    if debug:
        print(f"Extracted JD Skills: {extracted_jd_skills}")


    related_skills_map = get_related_skills()

    scored_candidates = score_skills_component(candidates, extracted_jd_skills, related_skills_map, debug=debug)

    return scored_candidates


def main():
    jd_skills_required = [
        "Programming Languages: Python, SQL",
        "Web Frameworks: Flask, FastAPI, Django (Optional)",
        "Databases: PostgreSQL, MySQL, MongoDB (Optional)",
        "API Development: RESTful APIs, API Design, Swagger/OpenAPI",
        "Version Control: Git, GitHub, GitLab",
        "Data Structures & Algorithms: DSA fundamentals, algorithm design, complexity analysis",
        "Testing: Unit Testing, Integration Testing, Test-Driven Development (TDD)"
    ]


    extracted_jd_skills = extract_skills_from_requirements(jd_skills_required)

    print(f"Extracted JD Skills: {extracted_jd_skills}")
    

    related_skills_map = get_related_skills()
    candidates = get_candidates()

   

    scored = final_skills_score(candidates, jd_skills_required, debug=True)
    # Each candidate now has:
    #   'raw_skill_score'      — raw % match
    #   'skill_percentile'     — percentile within pool
    #   'skill_weighted_score' — 0–35 scale for final integration

    print(scored)


if __name__ == "__main__":
    main()