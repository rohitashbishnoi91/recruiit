import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_seniority_mappings, get_candidates



def calculate_weighted_seniority_score(percentile_rank, max_points=5):
    """Scale percentile (0-100) to weighted points (0-5)"""
    return (percentile_rank / 100) * max_points

def extract_job_title_from_jd(jd_data):
    """Extract job title from JD structure"""
    return jd_data.get('job_title', '').strip()

def extract_years_experience_from_jd(jd_data):
    """Extract years of experience from JD structure"""
    years_exp = jd_data.get('years_of_experience', '').strip()
    return years_exp

def extract_seniority_from_title(title):
    """Enhanced extraction with proper error handling for regex groups"""
    if not title:
        return 'mid'  # Default to mid if no title
    
    seniority_mappings, experience_mappings = get_seniority_mappings()
    
    title_lower = title.lower().strip()
    
    # Enhanced pattern matching for level indicators (higher priority)
    level_patterns = [
        # Numeric patterns with role titles - 2 groups: (role, number)
        r'\b(engineer|developer|analyst|scientist|sde)\s+([1-9])\b',
        
        # L-level patterns - 1 group: (number)
        r'\bl([1-9])\b',
        
        # Level patterns - 1 group: (number)
        r'\blevel\s+([1-9])\b',
        
        # Grade patterns - 1 group: (number)
        r'\bgrade\s+([1-9])\b',
        
        # Roman numeral patterns - 2 groups: (role, roman)
        r'\b(engineer|developer|analyst|scientist)\s+(i{1,3}|iv|v|vi{0,3}|ix|x)\b',
        
        # Direct number patterns at end of title - 1 group: (number)
        r'\b([1-9])\s*$'
    ]
    
    # Try to extract level number first
    for pattern in level_patterns:
        match = re.search(pattern, title_lower)
        if match:
            # Get all groups and find the level number
            groups = match.groups()
            level_num = None
            
            # Extract level number from different group patterns
            if len(groups) == 1:
                # Single group patterns (L5, Level 4, Grade 3, number at end)
                level_num = groups[0]
            elif len(groups) == 2:
                # Two group patterns (Engineer 2, Engineer III)
                level_num = groups[1]  # Second group is the level
            
            if level_num:
                # Convert roman numerals to numbers
                roman_to_num = {
                    'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5',
                    'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'
                }
                
                if level_num in roman_to_num:
                    level_num = roman_to_num[level_num]
                
                # Map number to seniority level
                level_to_seniority = {
                    '1': 'entry',
                    '2': 'mid', '3': 'mid',
                    '4': 'senior', '5': 'senior',
                    '6': 'lead', '7': 'lead',
                    '8': 'management', '9': 'management', '10': 'management'
                }
                
                if level_num in level_to_seniority:
                    return level_to_seniority[level_num]
    
    # Fallback to original word-based matching
    for level, indicators in seniority_mappings.items():
        for indicator in indicators:
            if f" {indicator} " in f" {title_lower} " or title_lower.startswith(f"{indicator} ") or title_lower.endswith(f" {indicator}"):
                return level
    
    return 'mid'  # Default to mid level

def extract_seniority_from_experience(years_exp_str):
    """Extract seniority level from years of experience string"""
    if not years_exp_str:
        return 'mid'
    
    seniority_mappings, experience_mappings = get_seniority_mappings()
    
    # Parse years from string like "2+", "3-5", "5+ years"
    numbers = re.findall(r'\d+', years_exp_str)
    if not numbers:
        return 'mid'
    
    years = int(numbers[0])  # Take first number
    
    # Map years to seniority level
    for level, (min_years, max_years) in experience_mappings.items():
        if min_years <= years < max_years:
            return level
    
    return 'senior'  # Default for high experience

def get_jd_seniority_level(jd_data):
    """Get seniority level from JD using both title and experience"""
    jd_title = extract_job_title_from_jd(jd_data)
    years_exp = extract_years_experience_from_jd(jd_data)
    
    # Get seniority from title
    title_seniority = extract_seniority_from_title(jd_title)
    
    # Get seniority from experience
    exp_seniority = extract_seniority_from_experience(years_exp)
    
    # Priority: Title seniority first, then experience seniority
    if title_seniority != 'mid':  # If title has explicit seniority
        return title_seniority
    else:  # Use experience-based seniority
        return exp_seniority

def calculate_seniority_alignment_score(candidate_seniority, jd_seniority):
    """Calculate seniority alignment score (0-100)"""
    seniority_hierarchy = {
        'entry': 1,
        'mid': 2,
        'senior': 3,
        'lead': 4,
        'management': 5
    }
    
    candidate_level = seniority_hierarchy.get(candidate_seniority, 2)
    jd_level = seniority_hierarchy.get(jd_seniority, 2)
    
    level_diff = abs(candidate_level - jd_level)
    
    if level_diff == 0:
        return 100  # Perfect match
    elif level_diff == 1:
        return 80   # Adjacent level (good fit)
    elif level_diff == 2:
        return 50   # Two levels apart (moderate fit)
    elif level_diff == 3:
        return 25   # Three levels apart (poor fit)
    else:
        return 10   # Major mismatch

def calculate_seniority_raw_score(candidate_title, jd_data, debug=False):
    """Calculate raw seniority fit score (0-100)"""
    if not candidate_title:
        return 50.0  # Neutral score if no candidate title
    
    # Extract seniority levels
    candidate_seniority = extract_seniority_from_title(candidate_title)
    jd_seniority = get_jd_seniority_level(jd_data)
    
    # Calculate alignment score
    alignment_score = calculate_seniority_alignment_score(candidate_seniority, jd_seniority)
    
    if debug:
        jd_title = extract_job_title_from_jd(jd_data)
        years_exp = extract_years_experience_from_jd(jd_data)
        print(f"JD Title: '{jd_title}' + Experience: '{years_exp}' -> Seniority: {jd_seniority}")
        print(f"Candidate Title: '{candidate_title}' -> Seniority: {candidate_seniority}")
        print(f"Alignment Score: {alignment_score}")
        print("-" * 50)
    
    return alignment_score

def score_seniority_component(candidates, jd_data, debug=False):
    """Score seniority fit component for all candidates"""
    
    if debug:
        jd_title = extract_job_title_from_jd(jd_data)
        years_exp = extract_years_experience_from_jd(jd_data)
        print(f"JD Title: {jd_title}, Experience Required: {years_exp}")
        print("-" * 50)
    
    # Step 1: Calculate raw scores
    for candidate in candidates:
        candidate_title = candidate.get('Title', '')
        raw_score = calculate_seniority_raw_score(
            candidate_title, jd_data, debug=debug
        )
        candidate['raw_seniority_score'] = raw_score
        
        if debug:
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Title: {candidate_title}")
            print(f"Raw Score: {raw_score:.1f}")
            print("-" * 30)
    
    # Step 2: Calculate percentiles
    all_raw_scores = [c['raw_seniority_score'] for c in candidates]
    
    # Step 3: Calculate weighted scores
    for candidate in candidates:
        raw_score = candidate['raw_seniority_score']
        candidate['seniority_weighted_score'] = calculate_weighted_seniority_score(raw_score, max_points=5)

    if debug:
        print("Seniority scoring completed!")

    return candidates



def final_seniority_score(candidates, jd_data, debug=False):
    """Main function to call for seniority scoring"""
    
    if debug:
        print(f"Extracted Seniority Requirements: {jd_data}")
    
    # Score seniority component
    scored_candidates = score_seniority_component(candidates, jd_data, debug=debug)
    
    return scored_candidates



def main():
    jd_data = {
            "job_title": "Senior Python Developer",
            "years_of_experience": "5+",
            "qualifications": [
                "Bachelor's degree in Computer Science"
            ]
    }
    
    candidates = get_candidates()
    
    scored_candidates = final_seniority_score(candidates, jd_data, debug=True)
    
    scored_candidates.sort(key=lambda x: x['seniority_weighted_score'], reverse=True)
    
    print("\n" + "="*70)
    print("Seniority Fit Scores:")
    print("="*70)
    for candidate in scored_candidates:
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_seniority_score']:.1f}%, "
              f"Weighted: {candidate['seniority_weighted_score']:.1f}/5")

# if __name__ == "__main__":
#     main()
