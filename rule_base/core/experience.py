import re
from datetime import datetime
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_experience_mappings, get_candidates

# def calculate_percentile_rank(raw_score, all_raw_scores):
#     """Calculate percentile rank using mean for better tie handling"""
#     return percentileofscore(all_raw_scores, raw_score, kind='mean')

def calculate_weighted_experience_score(raw_score, max_points=25):
    """Scale percentile (0-100) to weighted points (0-25)"""
    return (raw_score / 100) * max_points

def extract_jd_experience_requirements(jd_data):
    """Extract experience requirements from JD"""
    years_exp = jd_data.get('years_of_experience', '').strip()
    job_title = jd_data.get('job_title', '').strip()
    qualifications = jd_data.get('qualifications', [])[0]
    
    # Parse experience requirement
    required_years = None
    if years_exp:
        # Extract first number from strings like "2+", "3-5", "5+ years"
        numbers = re.findall(r'\d+', years_exp)
        if numbers:
            required_years = int(numbers[0])
    
    # Extract from qualifications if not in years_of_experience
    if not required_years:
        for qual in qualifications:
            if 'years' in qual.lower() and ('experience' in qual.lower() or 'professional' in qual.lower()):
                numbers = re.findall(r'\d+', qual)
                if numbers:
                    required_years = int(numbers[0])
                    break
    
    return {
        'required_years': required_years or 0,
        'target_role': job_title.lower().strip(),
        'years_string': years_exp
    }

def normalize_job_title(title):
    """Normalize job title for better matching"""
    if not title:
        return ""
    
    title = title.lower().strip()
    
    # Remove seniority indicators for role matching
    seniority_indicators = [
        'senior', 'sr', 'sr.', 'junior', 'jr', 'jr.', 'lead', 'principal',
        'staff', 'chief', 'head', 'associate', 'assistant', 'i', 'ii', 'iii',
        'iv', 'v', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'
    ]
    
    for indicator in seniority_indicators:
        title = re.sub(rf'\b{re.escape(indicator)}\b', '', title)
    
    # Clean up extra spaces
    title = ' '.join(title.split())
    
    return title

def get_role_relevance(candidate_title, target_role, role_matrix):
    """Get relevance percentage between candidate title and target role"""
    candidate_normalized = normalize_job_title(candidate_title)
    target_normalized = normalize_job_title(target_role)
    
    # Direct lookup in matrix
    if target_normalized in role_matrix:
        for role, relevance in role_matrix[target_normalized].items():
            if role in candidate_normalized or candidate_normalized in role:
                return relevance
    
    # Reverse lookup
    if candidate_normalized in role_matrix:
        for role, relevance in role_matrix[candidate_normalized].items():
            if role in target_normalized or target_normalized in role:
                return relevance
    
    # Fallback: partial string matching
    if candidate_normalized == target_normalized:
        return 100
    elif candidate_normalized in target_normalized or target_normalized in candidate_normalized:
        return 80
    
    return 20  # Default low relevance

def calculate_position_duration(position, experience_obj, current_date=None):
    """Calculate duration of a position in years"""
    if not current_date:
        current_date = datetime.now()
    
    # Get start date
    start_year = position.get('startDateYear') or experience_obj.get('startDateYear')
    start_month = position.get('startDateMonth') or experience_obj.get('startDateMonth', 1)
    
    if not start_year:
        return 0
    
    start_date = datetime(start_year, start_month, 1)
    
    # Get end date
    end_year = position.get('endDateYear') or experience_obj.get('endDateYear')
    end_month = position.get('endDateMonth') or experience_obj.get('endDateMonth', 12)
    
    if end_year:
        end_date = datetime(end_year, end_month, 1)
    else:
        # Current role
        end_date = current_date
    
    # Calculate duration in years
    duration_days = (end_date - start_date).days
    duration_years = duration_days / 365.25
    
    return max(0, duration_years)

def calculate_recency_score(position, experience_obj, recency_weights, current_date=None):
    """Calculate recency score based on when the position ended"""
    if not current_date:
        current_date = datetime.now()
    
    # Get end date
    end_year = position.get('endDateYear') or experience_obj.get('endDateYear')
    end_month = position.get('endDateMonth') or experience_obj.get('endDateMonth', 12)
    
    if not end_year:
        # Current role
        return recency_weights['current']
    
    end_date = datetime(end_year, end_month, 1)
    months_since_end = (current_date - end_date).days / 30.44  # Average days per month
    
    if months_since_end <= 6:
        return recency_weights['0-6_months']
    elif months_since_end <= 12:
        return recency_weights['6-12_months']
    elif months_since_end <= 24:
        return recency_weights['1-2_years']
    elif months_since_end <= 36:
        return recency_weights['2-3_years']
    elif months_since_end <= 60:
        return recency_weights['3-5_years']
    else:
        return recency_weights['5+_years']

def calculate_relevant_experience(candidate, jd_requirements, role_matrix, recency_weights):
    """Calculate relevant experience duration and quality scores"""
    target_role = jd_requirements['target_role']
    
    total_relevant_years = 0
    max_relevance_score = 0
    best_recency_score = 0
    
    experiences = candidate.get('Experience', [])
    
    for exp in experiences:
        positions = exp.get('positions', [])
        
        for position in positions:
            title = position.get('title', '')
            
            # Calculate relevance
            relevance_pct = get_role_relevance(title, target_role, role_matrix)
            
            # Calculate duration
            duration_years = calculate_position_duration(position, exp)
            
            # Calculate recency
            recency_score = calculate_recency_score(position, exp, recency_weights)
            
            # Add to relevant experience (weighted by relevance)
            relevant_duration = duration_years * (relevance_pct / 100)
            total_relevant_years += relevant_duration
            
            # Track best scores
            max_relevance_score = max(max_relevance_score, relevance_pct)
            best_recency_score = max(best_recency_score, recency_score)
    
    return {
        'total_relevant_years': total_relevant_years,
        'max_relevance_score': max_relevance_score,
        'best_recency_score': best_recency_score
    }

def calculate_experience_raw_score(candidate, jd_data, debug=False):
    """Calculate raw experience alignment score (0-100)"""
    role_matrix, duration_mappings, tech_keywords, recency_weights = get_experience_mappings()
    
    # Extract JD requirements
    jd_requirements = extract_jd_experience_requirements(jd_data)
    
    # Calculate relevant experience
    exp_analysis = calculate_relevant_experience(
        candidate, jd_requirements, role_matrix, recency_weights
    )
    
    # Duration Score (50% weight)
    required_years = jd_requirements['required_years']
    relevant_years = exp_analysis['total_relevant_years']
    
    if required_years == 0:
        duration_score = 100  # No requirement
    elif relevant_years >= required_years:
        # Meets or exceeds requirement
        if relevant_years <= required_years * 2:
            duration_score = 100  # Perfect range
        else:
            duration_score = 90   # Over-qualified but good
    else:
        # Under-qualified
        ratio = relevant_years / required_years if required_years > 0 else 0
        duration_score = min(80, ratio * 100)
    
    # Relevance Score (30% weight)
    relevance_score = exp_analysis['max_relevance_score']
    
    # Recency Score (20% weight)
    recency_score = exp_analysis['best_recency_score']
    
    # Combined Score
    final_score = (duration_score * 0.5) + (relevance_score * 0.3) + (recency_score * 0.2)
    
    if debug:
        print(f"JD Requirements: {jd_requirements}")
        print(f"Relevant Experience: {relevant_years:.1f} years")
        print(f"Duration Score: {duration_score:.1f}")
        print(f"Relevance Score: {relevance_score:.1f}")
        print(f"Recency Score: {recency_score:.1f}")
        print(f"Final Score: {final_score:.1f}")
        print("-" * 50)
    
    return final_score

def score_experience_component(candidates, jd_data, debug=False):
    """Score experience alignment component for all candidates"""
    
    if debug:
        jd_requirements = extract_jd_experience_requirements(jd_data)
        print(f"JD Experience Requirements: {jd_requirements}")
        print("-" * 50)
    
    # Step 1: Calculate raw scores
    for candidate in candidates:
        raw_score = calculate_experience_raw_score(candidate, jd_data, debug=debug)
        candidate['raw_experience_score'] = raw_score
        
        if debug:
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Total Experience: {candidate.get('Experience in days', 0)} days")
            print(f"Raw Score: {raw_score:.1f}")
            print("-" * 30)
    
    # Step 2: Calculate percentiles
    all_raw_scores = [c['raw_experience_score'] for c in candidates]
    
    # Step 3: Calculate weighted scores
    for candidate in candidates:
        raw_score = candidate['raw_experience_score']
        candidate['experience_weighted_score'] = calculate_weighted_experience_score(raw_score, max_points=25)

    if debug:
        print("Experience scoring completed!")

    return candidates


def final_experience_score(candidates, jd_data, debug=False):
    """Main function to call for experience scoring"""
    
    # Extract experience requirements from JD
    # jd_requirements = extract_jd_experience_requirements(jd_data)
    
    if debug:
        print(f"Extracted Experience Requirements: {jd_data}")
    
    # Score experience component
    scored_candidates = score_experience_component(candidates, jd_data, debug=debug)
    
    return scored_candidates




def main():
    # Test with your JD data
    jd_data = {
            "job_title": "Python Developer",
            "years_of_experience": "2+",
            "qualifications": [
                "Minimum of 2 years of professional experience as a Python Developer."
            ]
    }
    
    # Get candidates from knowledge base
    candidates = get_candidates()
    
    # Score experience component
    scored_candidates = final_experience_score(candidates, jd_data, debug=True)
    
    # Sort by weighted score
    scored_candidates.sort(key=lambda x: x['experience_weighted_score'], reverse=True)
    
    print("\n" + "="*70)
    print("Experience Alignment Scores:")
    print("="*70)
    for candidate in scored_candidates[:10]:  # Show top 10
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_experience_score']:.1f}%, "
              f"Weighted: {candidate['experience_weighted_score']:.1f}/25")

# if __name__ == "__main__":
#     main()
