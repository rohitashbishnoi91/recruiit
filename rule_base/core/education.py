# from scipy.stats import percentileofscore  # Removed - not needed anymore
import re
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from knowledge_base import get_education_mappings, get_candidates

# def calculate_percentile_rank(raw_score, all_raw_scores):
#     """Calculate percentile rank using mean for better tie handling"""
#     return percentileofscore(all_raw_scores, raw_score, kind='mean')

def calculate_weighted_education_score(raw_score, max_points=10):
    """Convert raw score (0-100) directly to weighted points (0-10)"""
    return (raw_score / 100) * max_points

def extract_education_requirements_from_jd(jd_data):
    """Extract education requirements from JD qualifications"""
    qualifications = jd_data.get('qualifications', [])
    degree_mappings, field_mappings, cert_mappings = get_education_mappings()
    
    education_requirements = {
        'degree_levels': set(),
        'fields_of_study': set(),
        'has_education_requirement': False
    }
    
    for qualification in qualifications:
        if not qualification:
            continue
            
        qual_lower = qualification.lower()
        
        # Extract degree levels using comprehensive mappings
        for degree_term, standard_degree in degree_mappings.items():
            if degree_term in qual_lower:
                if standard_degree not in ['high_school', 'diploma', 'certificate']:
                    education_requirements['degree_levels'].add(standard_degree)
                    education_requirements['has_education_requirement'] = True
        
        # Extract fields using comprehensive mappings
        for field, variations in field_mappings.items():
            if any(variation in qual_lower for variation in variations):
                education_requirements['fields_of_study'].update(variations)
                education_requirements['has_education_requirement'] = True
    
    return education_requirements

def extract_candidate_education_enhanced(candidate):
    """Enhanced extraction of education and certifications from candidate"""
    education_list = candidate.get('Education', [])
    certifications_list = candidate.get('Certifications', [])
    degree_mappings, field_mappings, cert_categories = get_education_mappings()
    
    if not education_list and not certifications_list:
        return {
            'degree_levels': set(), 
            'fields_of_study': set(), 
            'certifications': set(),
            'certification_categories': set(),
            'has_education': False
        }
    
    candidate_education = {
        'degree_levels': set(),
        'fields_of_study': set(),
        'certifications': set(),
        'certification_categories': set(),
        'has_education': len(education_list) > 0
    }
    
    # Process Education using comprehensive mappings
    for edu in education_list:
        # Extract degree level
        degree = edu.get('degree', '').lower().strip()
        
        # Skip high school entries
        for degree_term, standard_degree in degree_mappings.items():
            if degree_term in degree:
                if standard_degree not in ['high_school']:  # Filter out high school
                    candidate_education['degree_levels'].add(standard_degree)
                break
        
        # Extract field of study using comprehensive mappings
        field = edu.get('fieldOfStudy', '').lower().strip()
        if field:
            candidate_education['fields_of_study'].add(field)
            
            # Find matching field categories
            for field_category, variations in field_mappings.items():
                if any(variation in field for variation in variations):
                    candidate_education['fields_of_study'].update(variations)
    
    # Process Certifications using comprehensive mappings
    for cert in certifications_list:
        cert_name = cert.get('name', '').lower().strip()
        cert_authority = cert.get('authority', '').lower().strip()
        
        if cert_name:
            candidate_education['certifications'].add(cert_name)
        if cert_authority:
            candidate_education['certifications'].add(cert_authority)
        
        # Categorize certifications
        for category, cert_terms in cert_categories.items():
            if any(term in cert_name or term in cert_authority for term in cert_terms):
                candidate_education['certification_categories'].add(category)
    
    return candidate_education

def calculate_education_raw_score_enhanced(candidate_education, jd_requirements, debug=False):
    """Enhanced education scoring with degree + field + certification"""
    
    if not jd_requirements['has_education_requirement']:
        # No education requirement - score based on what candidate has
        base_score = 90.0 if candidate_education['has_education'] else 60.0
        cert_bonus = min(10, len(candidate_education['certification_categories']) * 3)
        return min(100.0, base_score + cert_bonus)
    
    if not candidate_education['has_education']:
        # JD requires education but candidate has none
        cert_bonus = min(40, len(candidate_education['certification_categories']) * 10)
        return cert_bonus
    
    # Weighted scoring: 60% degree + 30% field + 10% certifications
    degree_score = 0
    field_score = 0
    certification_score = 0
    
    # Degree level matching (60% weight) - EXACT MATCH gets priority
    if jd_requirements['degree_levels']:
        degree_matches = candidate_education['degree_levels'].intersection(jd_requirements['degree_levels'])
        
        if degree_matches:
            degree_score = 100  # PERFECT EXACT MATCH
        else:
            # Qualification hierarchy with business logic
            candidate_degrees = candidate_education['degree_levels']
            required_degrees = jd_requirements['degree_levels']
            
            if 'bachelor' in required_degrees:
                if 'master' in candidate_degrees:
                    degree_score = 80  # Over-qualified: might have higher salary expectations
                elif 'phd' in candidate_degrees:
                    degree_score = 70  # Significantly over-qualified: likely to leave
                elif 'diploma' in candidate_degrees:
                    degree_score = 50  # Under-qualified but some relevant education
                else:
                    degree_score = 30  # Wrong level entirely
                    
            elif 'master' in required_degrees:
                if 'phd' in candidate_degrees:
                    degree_score = 85  # Slightly over-qualified but acceptable
                elif 'bachelor' in candidate_degrees:
                    degree_score = 65  # Under-qualified but trainable
                elif 'diploma' in candidate_degrees:
                    degree_score = 40  # Significantly under-qualified
                else:
                    degree_score = 30  # Wrong level entirely
                    
            elif 'phd' in required_degrees:
                if 'master' in candidate_degrees:
                    degree_score = 75  # Under-qualified for PhD role
                elif 'bachelor' in candidate_degrees:
                    degree_score = 50  # Significantly under-qualified
                else:
                    degree_score = 30  # Wrong level entirely
            else:
                degree_score = 40  # Has education but unclear level
    else:
        degree_score = 85  # No specific degree requirement
    
    # Field relevance matching (30% weight)
    if jd_requirements['fields_of_study']:
        field_matches = candidate_education['fields_of_study'].intersection(jd_requirements['fields_of_study'])
        
        if field_matches:
            field_score = 100  # Perfect field match
        else:
            # Check for related fields
            candidate_fields = candidate_education['fields_of_study']
            required_fields = jd_requirements['fields_of_study']
            
            # Cross-field relationship scoring
            related_score = 0
            for req_field in required_fields:
                for cand_field in candidate_fields:
                    if ('computer' in req_field and 'computer' in cand_field) or \
                       ('engineering' in req_field and 'engineering' in cand_field) or \
                       ('technology' in req_field and 'technology' in cand_field):
                        related_score = max(related_score, 70)
                    elif ('science' in req_field and 'science' in cand_field):
                        related_score = max(related_score, 60)
            
            field_score = related_score if related_score > 0 else 40
    else:
        field_score = 85  # No specific field requirement
    
    # Certification scoring (10% weight)
    cert_categories_count = len(candidate_education['certification_categories'])
    if cert_categories_count == 0:
        certification_score = 60  # No certifications
    elif cert_categories_count <= 2:
        certification_score = 75  # Few relevant certifications
    elif cert_categories_count <= 4:
        certification_score = 90  # Good number of certifications
    else:
        certification_score = 100  # Many relevant certifications
    
    # Combined weighted score
    final_score = (degree_score * 0.6) + (field_score * 0.3) + (certification_score * 0.1)
    
    if debug:
        print(f"Degree Score: {degree_score:.1f} (60% weight)")
        print(f"Field Score: {field_score:.1f} (30% weight)")  
        print(f"Certification Score: {certification_score:.1f} (10% weight)")
        print(f"Final Education Score: {final_score:.1f}")
    
    return final_score

def score_education_component_enhanced(candidates, jd_data, debug=False):
    """Enhanced education scoring with comprehensive mappings"""
    
    # Extract JD requirements
    jd_requirements = extract_education_requirements_from_jd(jd_data)
    
    if debug:
        print(f"JD Education Requirements: {jd_requirements}")
        print("-" * 50)
    
    # Step 1: Calculate raw scores
    for candidate in candidates:
        candidate_education = extract_candidate_education_enhanced(candidate)
        raw_score = calculate_education_raw_score_enhanced(
            candidate_education, jd_requirements, debug=debug
        )
        candidate['raw_education_score'] = raw_score
        
        if debug:
            print(f"Candidate: {candidate.get('Name', 'Unknown')}")
            print(f"Education: {candidate_education}")
            print(f"Raw Score: {raw_score:.1f}")
            print("-" * 30)
    
    # Step 2: Convert raw scores directly to weighted scores (NO PERCENTILES)
    for candidate in candidates:
        raw_score = candidate['raw_education_score']
        candidate['education_weighted_score'] = calculate_weighted_education_score(raw_score, max_points=10)

    if debug:
        print("Education scoring completed!")

    return candidates

def final_education_score(candidates, jd_data, debug=False):
    """Main function to call for education scoring"""
    
    if debug:
        print(f"Extracted Education Requirements: {jd_data}")
    
    # Score education component
    scored_candidates = score_education_component_enhanced(candidates, jd_data, debug=debug)
    
    return scored_candidates

def main():
    # Test with enhanced JD requirements
    jd_data = {
        "qualifications": [
            "Bachelor's degree in Computer Science, Software Engineering, or a related field.",
            "Minimum of 2 years of professional experience as a Python Developer.",
            "Relevant certifications in cloud technologies (AWS, Azure) preferred."
        ]
    }
    
    # Sample candidates from your actual data
    candidates = get_candidates()
    
    # Score education component
    scored_candidates = final_education_score(candidates, jd_data, debug=True)
    
    # Sort by weighted score
    scored_candidates.sort(key=lambda x: x['education_weighted_score'], reverse=True)
    
    print("\n" + "="*70)
    print("Final Enhanced Education Match Scores:")
    print("="*70)
    for candidate in scored_candidates[:10]:  # Show top 10
        print(f"{candidate['Name']}: "
              f"Raw: {candidate['raw_education_score']:.1f}%, "
              f"Weighted: {candidate['education_weighted_score']:.1f}/10")

# if __name__ == "__main__":
#     main()
