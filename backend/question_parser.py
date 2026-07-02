"""
Question parsing utilities for extracting parameters from user questions.
This module provides functions to extract metadata like origin, destination,
timespan, and other parameters from natural language questions.
"""

import re
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Country name to ISO3 code mapping (common countries)
COUNTRY_MAPPING = {
    # Common country names and their ISO3 codes
    'france': 'FRA', 'french': 'FRA',
    'germany': 'DEU', 'german': 'DEU',
    'united states': 'USA', 'usa': 'USA', 'america': 'USA', 'us': 'USA',
    'united kingdom': 'GBR', 'uk': 'GBR', 'britain': 'GBR',
    'syria': 'SYR', 'syrian': 'SYR',
    'afghanistan': 'AFG', 'afghan': 'AFG',
    'ukraine': 'UKR', 'ukrainian': 'UKR',
    'sudan': 'SDN', 'sudanese': 'SDN',
    'south sudan': 'SSD',
    'venezuela': 'VEN', 'venezuelan': 'VEN',
    'myanmar': 'MMR', 'burma': 'MMR', 'burmese': 'MMR',
    'somalia': 'SOM', 'somali': 'SOM',
    'democratic republic of congo': 'COD', 'drc': 'COD', 'congo': 'COD',
    'yemen': 'YEM', 'yemeni': 'YEM',
    'ethiopia': 'ETH', 'ethiopian': 'ETH',
    'colombia': 'COL', 'colombian': 'COL',
    'turkey': 'TUR', 'turkish': 'TUR',
    'lebanon': 'LBN', 'lebanese': 'LBN',
    'jordan': 'JOR', 'jordanian': 'JOR',
    'pakistan': 'PAK', 'pakistani': 'PAK',
    'bangladesh': 'BGD', 'bangladeshi': 'BGD',
    'iran': 'IRN', 'iranian': 'IRN',
    'iraq': 'IRQ', 'iraqi': 'IRQ',
    'egypt': 'EGY', 'egyptian': 'EGY',
    'chad': 'TCD', 'chadian': 'TCD',
    'kenya': 'KEN', 'kenyan': 'KEN',
    'uganda': 'UGA', 'ugandan': 'UGA',
    'libya': 'LBY', 'libyan': 'LBY',
    'niger': 'NER', 'nigerien': 'NER',
    'cameroon': 'CMR', 'cameroonian': 'CMR',
    'burundi': 'BDI', 'burundian': 'BDI',
    'central african republic': 'CAF', 'car': 'CAF',
    'eritrea': 'ERI', 'eritrean': 'ERI',
    'mali': 'MLI', 'malian': 'MLI',
    'nigeria': 'NGA', 'nigerian': 'NGA',
    'russia': 'RUS', 'russian': 'RUS',
    'china': 'CHN', 'chinese': 'CHN',
    'india': 'IND', 'indian': 'IND',
    'canada': 'CAN', 'canadian': 'CAN',
    'australia': 'AUS', 'australian': 'AUS',
    'brazil': 'BRA', 'brazilian': 'BRA',
    'mexico': 'MEX', 'mexican': 'MEX',
    'japan': 'JPN', 'japanese': 'JPN',
    'greece': 'GRC', 'greek': 'GRC',
    'italy': 'ITA', 'italian': 'ITA',
    'spain': 'ESP', 'spanish': 'ESP',
    'sweden': 'SWE', 'swedish': 'SWE',
    'norway': 'NOR', 'norwegian': 'NOR',
    'denmark': 'DNK', 'danish': 'DNK',
    'finland': 'FIN', 'finnish': 'FIN',
    'netherlands': 'NLD', 'dutch': 'NLD',
    'belgium': 'BEL', 'belgian': 'BEL',
    'switzerland': 'CHE', 'swiss': 'CHE',
    'austria': 'AUT', 'austrian': 'AUT',
    'poland': 'POL', 'polish': 'POL',
    'hungary': 'HUN', 'hungarian': 'HUN',
    'romania': 'ROU', 'romanian': 'ROU',
    'bulgaria': 'BGR', 'bulgarian': 'BGR',
    'czech republic': 'CZE', 'czech': 'CZE',
    'slovakia': 'SVK', 'slovak': 'SVK',
    'croatia': 'HRV', 'croatian': 'HRV',
    'serbia': 'SRB', 'serbian': 'SRB',
    'bosnia': 'BIH', 'bosnian': 'BIH',
    'albania': 'ALB', 'albanian': 'ALB',
    'montenegro': 'MNE', 'montenegrin': 'MNE',
    'north macedonia': 'MKD', 'macedonian': 'MKD',
    'slovenia': 'SVN', 'slovenian': 'SVN',
    'estonia': 'EST', 'estonian': 'EST',
    'latvia': 'LVA', 'latvian': 'LVA',
    'lithuania': 'LTU', 'lithuanian': 'LTU',
    'ireland': 'IRL', 'irish': 'IRL',
    'portugal': 'PRT', 'portuguese': 'PRT',
    'argentina': 'ARG', 'argentine': 'ARG',
    'chile': 'CHL', 'chilean': 'CHL',
    'peru': 'PER', 'peruvian': 'PER',
    'colombia': 'COL', 'colombian': 'COL',
    'venezuela': 'VEN', 'venezuelan': 'VEN',
    'ecuador': 'ECU', 'ecuadorian': 'ECU',
    'bolivia': 'BOL', 'bolivian': 'BOL',
    'paraguay': 'PRY', 'paraguayan': 'PRY',
    'uruguay': 'URY', 'uruguayan': 'URY',
    'saudi arabia': 'SAU', 'saudi': 'SAU',
    'united arab emirates': 'ARE', 'uae': 'ARE', 'emirati': 'ARE',
    'qatar': 'QAT', 'qatari': 'QAT',
    'kuwait': 'KWT', 'kuwaiti': 'KWT',
    'oman': 'OMN', 'omani': 'OMN',
    'israel': 'ISR', 'israeli': 'ISR',
    'palestine': 'PSE', 'palestinian': 'PSE',
    'lebanon': 'LBN', 'lebanese': 'LBN',
    'syria': 'SYR', 'syrian': 'SYR',
    'jordan': 'JOR', 'jordanian': 'JOR',
    'egypt': 'EGY', 'egyptian': 'EGY',
    'turkey': 'TUR', 'turkish': 'TUR',
    'iran': 'IRN', 'iranian': 'IRN',
    'iraq': 'IRQ', 'iraqi': 'IRQ',
    'yemen': 'YEM', 'yemeni': 'YEM',
    'afghanistan': 'AFG', 'afghan': 'AFG',
    'pakistan': 'PAK', 'pakistani': 'PAK',
    'india': 'IND', 'indian': 'IND',
    'bangladesh': 'BGD', 'bangladeshi': 'BGD',
    'sri lanka': 'LKA', 'sri lankan': 'LKA',
    'nepal': 'NPL', 'nepali': 'NPL',
    'bhutan': 'BTN', 'bhutanese': 'BTN',
    'myanmar': 'MMR', 'burma': 'MMR', 'burmese': 'MMR',
    'thailand': 'THA', 'thai': 'THA',
    'vietnam': 'VNM', 'vietnamese': 'VNM',
    'laos': 'LAO', 'laotian': 'LAO',
    'cambodia': 'KHM', 'cambodian': 'KHM',
    'philippines': 'PHL', 'filipino': 'PHL',
    'indonesia': 'IDN', 'indonesian': 'IDN',
    'malaysia': 'MYS', 'malaysian': 'MYS',
    'singapore': 'SGP', 'singaporean': 'SGP',
    'south korea': 'KOR', 'korea': 'KOR', 'korean': 'KOR',
    'north korea': 'PRK', 'dprk': 'PRK',
    'mongolia': 'MNG', 'mongolian': 'MNG',
    'kazakhstan': 'KAZ', 'kazakh': 'KAZ',
    'uzbekistan': 'UZB', 'uzbek': 'UZB',
    'turkmenistan': 'TKM', 'turkmen': 'TKM',
    'kyrgyzstan': 'KGZ', 'kyrgyz': 'KGZ',
    'tajikistan': 'TJK', 'tajik': 'TJK',
    'georgia': 'GEO', 'georgian': 'GEO',
    'armenia': 'ARM', 'armenian': 'ARM',
    'azerbaijan': 'AZE', 'azeri': 'AZE',
}

# Population types for UNHCR data
POPULATION_TYPES = [
    'refugees', 'asylum_seekers', 'idps', 'returnees', 'stateless',
    'venezuelans_displaced_abroad', 'other_people_in_need'
]

def extract_question_parameters(question: str) -> Dict[str, Optional[str]]:
    """
    Extract metadata parameters from a user question.
    
    Args:
        question: The user's question in natural language
        
    Returns:
        Dictionary containing extracted parameters:
        - origin: Country of origin (ISO3 code)
        - destination: Country of asylum (ISO3 code) 
        - timespan: Time period (years or range)
        - topic: Main topic/subject
        - population_type: Type of population
    """
    
    # Initialize with None values
    params = {
        'origin': None,
        'destination': None, 
        'timespan': None,
        'topic': None,
        'population_type': None
    }
    
    # Convert to lowercase for case-insensitive matching
    question_lower = question.lower()
    
    # Extract population type
    for pop_type in POPULATION_TYPES:
        if pop_type in question_lower:
            params['population_type'] = pop_type
            break
    
    # If no specific population type found, default to refugees for refugee-related questions
    if not params['population_type'] and any(keyword in question_lower for keyword in ['refugee', 'asylum', 'displaced', 'migration']):
        params['population_type'] = 'refugees'
    
    # Extract countries using predefined patterns
    params.update(extract_countries_from_question(question_lower))
    
    # Extract timespan
    params['timespan'] = extract_timespan_from_question(question_lower)
    
    # Extract topic (simplified - could be enhanced with NLP)
    topic_keywords = ['trends', 'demographics', 'solutions', 'returns', 'resettlement', 'education', 'health', 'employment']
    for keyword in topic_keywords:
        if keyword in question_lower:
            params['topic'] = keyword
            break
    
    # If no topic found, try to infer from question structure
    if not params['topic']:
        if any(word in question_lower for word in ['trend', 'over time', 'year', 'evolution', 'change']):
            params['topic'] = 'trends'
        elif any(word in question_lower for word in ['demographic', 'age', 'gender', 'breakdown', 'distribution']):
            params['topic'] = 'demographics'
    
    logger.debug(f"Extracted parameters from question '{question}': {params}")
    
    return params

def extract_countries_from_question(question: str) -> Dict[str, Optional[str]]:
    """
    Extract origin and destination countries from question text.
    
    Args:
        question: Question text in lowercase
        
    Returns:
        Dictionary with 'origin' and 'destination' ISO3 codes
    """
    
    countries = {'origin': None, 'destination': None}
    
    # Patterns that indicate origin (from, fleeing, originating)
    origin_patterns = [
        r'from\s+([\w\s]+)',
        r'fleeing\s+([\w\s]+)',
        r'originating\s+from\s+([\w\s]+)',
        r'([\w\s]+)\s+(refugees|asylum seekers|migrants|displaced)',
        r'(refugees|asylum seekers|migrants|displaced)\s+from\s+([\w\s]+)'
    ]
    
    # Patterns that indicate destination (to, in, arriving, hosted)
    destination_patterns = [
        r'to\s+([\w\s]+)',
        r'in\s+([\w\s]+)',
        r'arriving\s+in\s+([\w\s]+)',
        r'hosted\s+by\s+([\w\s]+)',
        r'in\s+([\w\s]+)\s+(refugees|asylum seekers|migrants)',
        r'(refugees|asylum seekers|migrants|displaced)\s+in\s+([\w\s]+)'
    ]
    
    # Try to extract origin
    for pattern in origin_patterns:
        match = re.search(pattern, question)
        if match:
            country_name = match.group(1).strip()
            iso3_code = lookup_country_iso3(country_name)
            if iso3_code:
                countries['origin'] = iso3_code
                break
    
    # Try to extract destination
    for pattern in destination_patterns:
        match = re.search(pattern, question)
        if match:
            country_name = match.group(1).strip()
            iso3_code = lookup_country_iso3(country_name)
            if iso3_code:
                countries['destination'] = iso3_code
                break
    
    # Special case: "Refugees from X in Y" pattern
    from_in_pattern = r'from\s+([\w\s]+?)\s+in\s+([\w\s]+)'
    match = re.search(from_in_pattern, question)
    if match:
        origin_name = match.group(1).strip()
        dest_name = match.group(2).strip()
        
        origin_iso3 = lookup_country_iso3(origin_name)
        dest_iso3 = lookup_country_iso3(dest_name)
        
        if origin_iso3:
            countries['origin'] = origin_iso3
        if dest_iso3:
            countries['destination'] = dest_iso3
    
    return countries

def lookup_country_iso3(country_name: str) -> Optional[str]:
    """
    Lookup country ISO3 code from country name.
    
    Args:
        country_name: Country name (lowercase)
        
    Returns:
        ISO3 code if found, None otherwise
    """
    
    # Clean up the country name
    clean_name = country_name.strip().lower()
    
    # Remove common suffixes
    for suffix in ['the', 'of', 'and', 'republic', 'kingdom', 'states', 'united']:
        if clean_name.endswith(suffix):
            clean_name = clean_name[:-len(suffix)].strip()
    
    # Check direct matches
    if clean_name in COUNTRY_MAPPING:
        return COUNTRY_MAPPING[clean_name]
    
    # Check if it's a partial match (e.g., "united states" -> "usa")
    for key, value in COUNTRY_MAPPING.items():
        if clean_name in key or key.startswith(clean_name):
            return value
    
    # Check for common alternative names
    alternatives = {
        'us': 'USA', 'usa': 'USA', 'america': 'USA',
        'uk': 'GBR', 'britain': 'GBR',
        'drc': 'COD', 'congo': 'COD',
        'burma': 'MMR',
        'holland': 'NLD',
        'netherlands': 'NLD',
        'switzerland': 'CHE',
        'czech republic': 'CZE',
        'south korea': 'KOR',
        'north korea': 'PRK',
        'dprk': 'PRK',
        'roe': 'KOR',
        'rca': 'CAF',
        'car': 'CAF'
    }
    
    if clean_name in alternatives:
        return alternatives[clean_name]
    
    return None

def extract_timespan_from_question(question: str) -> Optional[str]:
    """
    Extract timespan information from question text.
    
    Args:
        question: Question text in lowercase
        
    Returns:
        Timespan as year range or specific years, None if not found
    """
    
    # Common time patterns and their corresponding year ranges
    time_patterns = {
        # Past X years patterns
        r'past\s+(\d+)\s+years': lambda n: generate_year_range(int(n)),
        r'last\s+(\d+)\s+years': lambda n: generate_year_range(int(n)),
        r'previous\s+(\d+)\s+years': lambda n: generate_year_range(int(n)),
        r'recent\s+(\d+)\s+years': lambda n: generate_year_range(int(n)),
        
        # Specific year ranges
        r'from\s+(\d{4})\s+to\s+(\d{4})': lambda y1, y2: f"{y1}-{y2}",
        r'between\s+(\d{4})\s+and\s+(\d{4})': lambda y1, y2: f"{y1}-{y2}",
        r'(\d{4})\s*[-–]\s*(\d{4})': lambda y1, y2: f"{y1}-{y2}",
        
        # Decade patterns
        r'(\d{4})s': lambda decade: f"{decade}-{int(decade)+9}",
        r'the\s+(\d{4})s': lambda decade: f"{decade}-{int(decade)+9}",
        
        # Specific year mentions
        r'in\s+(\d{4})': lambda year: year,
        r'for\s+(\d{4})': lambda year: year,
        r'during\s+(\d{4})': lambda year: year,
        
        # Year lists
        r'(\d{4})\s*,\s*(\d{4})\s*,\s*(\d{4})': lambda y1, y2, y3: f"{y1},{y2},{y3}",
        r'(\d{4})\s*,\s*(\d{4})': lambda y1, y2: f"{y1},{y2}",
    }
    
    # Try each pattern
    for pattern, handler in time_patterns.items():
        match = re.search(pattern, question)
        if match:
            try:
                args = match.groups()
                if len(args) == 1:
                    return handler(args[0])
                elif len(args) == 2:
                    return handler(args[0], args[1])
                elif len(args) == 3:
                    return handler(args[0], args[1], args[2])
            except Exception as e:
                logger.warning(f"Error handling time pattern {pattern}: {e}")
                continue
    
    # Check for common phrases
    common_phrases = {
        'past 10 years': '2015-2024',
        'last 10 years': '2015-2024',
        'past 5 years': '2020-2024', 
        'last 5 years': '2020-2024',
        'recent years': '2022-2024',
        'last year': '2024',
        'this year': '2024',
        'current year': '2024',
        '2020-2024': '2020-2024',
        '2015-2024': '2015-2024',
        '2010-2024': '2010-2024'
    }
    
    for phrase, years in common_phrases.items():
        if phrase in question:
            return years
    
    # Default to recent years if no specific timespan found
    return '2020-2024'

def generate_year_range(n_years: int) -> str:
    """
    Generate a year range string for the past N years.
    
    Args:
        n_years: Number of years
        
    Returns:
        Year range string (e.g., '2015-2024' for 10 years)
    """
    
    current_year = 2024  # Update this as needed
    start_year = current_year - n_years + 1
    
    if start_year < 2000:  # Don't go too far back for UNHCR data
        start_year = 2000
    
    if start_year == current_year:
        return str(current_year)
    else:
        return f"{start_year}-{current_year}"

def auto_complete_parameters(
    existing_params: Dict[str, Optional[str]],
    missing_params: List[str],
    question: str
) -> Dict[str, Optional[str]]:
    """
    Automatically complete missing parameters by extracting from question or using defaults.
    
    Args:
        existing_params: Parameters that are already present
        missing_params: List of parameter names that are missing
        question: Original question text
        
    Returns:
        Completed parameters dictionary
    """
    
    completed_params = existing_params.copy()
    question_lower = question.lower()
    
    for param in missing_params:
        if param == 'coo':
            # Try to get from origin first, then extract from question
            if not completed_params.get('coo'):
                if completed_params.get('origin'):
                    completed_params['coo'] = completed_params['origin']
                else:
                    countries = extract_countries_from_question(question_lower)
                    if countries.get('origin'):
                        completed_params['coo'] = countries['origin']
                    elif 'fra' in question_lower or 'france' in question_lower:
                        completed_params['coo'] = 'FRA'
                    else:
                        # Default to common refugee origin country
                        completed_params['coo'] = 'SYR'  # Syria as default
                
        elif param == 'coa':
            # Try to get from destination first, then extract from question
            if not completed_params.get('coa'):
                if completed_params.get('destination'):
                    completed_params['coa'] = completed_params['destination']
                else:
                    countries = extract_countries_from_question(question_lower)
                    if countries.get('destination'):
                        completed_params['coa'] = countries['destination']
                    else:
                        # Default to common host country
                        completed_params['coa'] = 'TUR'  # Turkey as default
                
        elif param == 'years':
            # Try to get from timespan first, then extract from question
            if not completed_params.get('years'):
                if completed_params.get('timespan'):
                    completed_params['years'] = completed_params['timespan']
                else:
                    timespan = extract_timespan_from_question(question_lower)
                    if timespan:
                        completed_params['years'] = timespan
                    else:
                        completed_params['years'] = '2020-2024'  # Default recent years
                
        elif param == 'population_types':
            # Try to get from population_type first, then default
            if not completed_params.get('population_types'):
                if completed_params.get('population_type'):
                    # Map single population_type to list
                    pop_type = completed_params['population_type']
                    completed_params['population_types'] = [pop_type]
                else:
                    # Default to refugees if not specified
                    completed_params['population_types'] = ['refugees']
    
    return completed_params

def get_required_params_for_tool(tool_name: str) -> List[str]:
    """
    Get the list of required parameters for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        List of required parameter names
    """
    
    tool_requirements = {
        'get_population_trends': ['coo', 'coa', 'years', 'population_types'],
        'get_population_data': ['coo', 'coa', 'year'],
        'get_demographic_breakdown': ['coo', 'coa', 'year'],
        'get_solutions': ['coo', 'coa', 'year'],
        'get_data_for_story': ['question'],
        'generate_analytical_story': ['data', 'question'],
        'create_quarto_notebook': ['story_content', 'title']
    }
    
    return tool_requirements.get(tool_name, [])

# Test the parser
if __name__ == "__main__":
    # Test cases
    test_questions = [
        "Refugees from France in the past 10 years",
        "Asylum seekers in Germany from Syria in 2020-2024",
        "Trends of displaced people from Ukraine to Poland since 2022",
        "Demographic breakdown of refugees in Lebanon",
        "Solutions for Venezuelan migrants in Colombia"
    ]
    
    print("Testing question parser...")
    print("=" * 60)
    
    for question in test_questions:
        params = extract_question_parameters(question)
        print(f"Question: {question}")
        print(f"Parameters: {params}")
        print()