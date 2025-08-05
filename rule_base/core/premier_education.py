from scipy.stats import percentileofscore
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_premier_institutions, get_candidates


def calculate_weighted_premier_education_score(raw_score, max_points=5):
    """Convert raw score (0-100) directly to weighted points (0-5)"""
    return (raw_score / 100) * max_points

def extract_candidate_institutions(candidate):
    """Extract educational institutions from candidate profile"""
    education_list = candidate.get('Education', [])
    institutions = set()
    
    for edu in education_list:
        if 'school' in edu and 'name' in edu['school']:
            institution_name = edu['school']['name'].lower().strip()
            institution_name = institution_name.replace(',', '').replace('.', '').replace('-', ' ')
            institution_name = ' '.join(institution_name.split())
            institutions.add(institution_name)
    
    return institutions

def normalize_institution_name(name):
    """Normalize institution name for better matching"""
    name = name.lower().strip()
    name = name.replace(',', '').replace('.', '').replace('-', ' ')
    name = name.replace('&', 'and')
    name = ' '.join(name.split())
    return name

def calculate_premier_education_raw_score(candidate, category_a, category_b, debug=False):
    """Calculate raw premier education score with Category A/B differentiation"""
    candidate_institutions = extract_candidate_institutions(candidate)
    
    if not candidate_institutions:
        return 0
    
    max_score = 0
    matched_category = None
    matched_institution = None
    
    for institution in candidate_institutions:
        normalized_candidate = normalize_institution_name(institution)
        
        # Check Category A (100 points)
        for premier_a_key, variations in category_a.items():
            normalized_premier_key = normalize_institution_name(premier_a_key)
            
            if normalized_premier_key == normalized_candidate:
                if debug:
                    print(f"Category A Match: '{institution}' matches '{premier_a_key}'")
                max_score = 100
                matched_category = "A"
                matched_institution = premier_a_key
                break
            
            for variation in variations:
                normalized_variation = normalize_institution_name(variation)
                if (normalized_variation == normalized_candidate or 
                    normalized_variation in normalized_candidate or
                    normalized_candidate in normalized_variation):
                    
                    if debug:
                        print(f"Category A Match: '{institution}' matches '{variation}' (variant of {premier_a_key})")
                    max_score = 100
                    matched_category = "A"
                    matched_institution = premier_a_key
                    break
            
            if max_score == 100:
                break
        
        # Check Category B only if no Category A match (75 points)
        if max_score < 100:
            for premier_b_key, variations in category_b.items():
                normalized_premier_key = normalize_institution_name(premier_b_key)
                
                if normalized_premier_key == normalized_candidate:
                    if debug:
                        print(f"Category B Match: '{institution}' matches '{premier_b_key}'")
                    max_score = 75
                    matched_category = "B"
                    matched_institution = premier_b_key
                    break
                
                for variation in variations:
                    normalized_variation = normalize_institution_name(variation)
                    if (normalized_variation == normalized_candidate or 
                        normalized_variation in normalized_candidate or
                        normalized_candidate in normalized_variation):
                        
                        if debug:
                            print(f"Category B Match: '{institution}' matches '{variation}' (variant of {premier_b_key})")
                        max_score = 75
                        matched_category = "B"
                        matched_institution = premier_b_key
                        break
                
                if max_score == 75:
                    break
    
    if debug and max_score == 0:
        print(f"NO PREMIER MATCH: {candidate_institutions}")
    
    return max_score

def score_premier_education_component(candidates, debug=False):
    """Score premier education component for all candidates"""
    
    category_a, category_b = get_premier_institutions()

    # Step 1: Calculate raw scores
    for candidate in candidates:
        raw_score = calculate_premier_education_raw_score(candidate, category_a, category_b, debug=debug)
        candidate['raw_premier_education_score'] = raw_score
        
        if debug:
            institutions = extract_candidate_institutions(candidate)
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Institutions: {institutions}")
            print(f"Raw Score: {raw_score}")
            print("-" * 50)
    
    # Step 2: Calculate percentiles
    all_raw_scores = [c['raw_premier_education_score'] for c in candidates]
    
    # Step 3: Calculate weighted scores
    for candidate in candidates:
        raw_score = candidate['raw_premier_education_score']
        candidate['premier_education_weighted_score'] = calculate_weighted_premier_education_score(raw_score, max_points=5)

    if debug:
        print("Premier education scoring completed!")

    return candidates



def final_premier_education_score(candidates, debug=False):
    """Main function to call for premier education scoring"""
    
    if debug:
        print("Premier education scoring does not depend on JD data")
    
    # Score premier education component
    scored_candidates = score_premier_education_component(candidates, debug=debug)
    
    return scored_candidates





def main():
    candidates = get_candidates()
    
    # Score premier education component
    scored_candidates = final_premier_education_score(candidates, debug=True)
    
    print("\nPremier Education Scores:")
    for candidate in scored_candidates:
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_premier_education_score']:.1f}%, "
              f"Weighted: {candidate['premier_education_weighted_score']:.1f}/5")

# if __name__ == "__main__":
#     main()
