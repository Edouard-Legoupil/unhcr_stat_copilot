"""
Tool: get_suggested_questions
Get suggested questions and query examples based on topics or data types.
"""

from typing import Any, Optional


def get_suggested_questions_tool(
    topic: Optional[str] = None,
    data_type: Optional[str] = None,
    limit: int = 5
) -> dict[str, Any]:
    """
    Get suggested questions based on topic or data type.
    
    Args:
        topic: Topic area
        data_type: Type of data
        limit: Maximum number of suggestions to return
    
    Returns:
        List of suggested questions
    """
    suggested_questions = {
        'refugees': [
            'What is the total number of refugees from Syria?',
            'How many refugees are in Turkey?',
            'What are the top 5 countries hosting refugees?',
            'What is the trend in refugee numbers over the past 5 years?',
            'Which countries have the most refugees per capita?'
        ],
        'asylum': [
            'How many asylum applications were filed in 2024?',
            'What is the recognition rate for asylum seekers from Afghanistan?',
            'Which countries receive the most asylum applications?',
            'What are the main countries of origin for asylum seekers in Europe?',
            'How has the number of asylum applications changed over time?'
        ],
        'demographics': [
            'What is the age distribution of refugees?',
            'What percentage of displaced persons are children?',
            'What is the gender breakdown of asylum seekers?',
            'How does the demographic composition vary by country?',
            'What are the most common age groups among refugees?'
        ],
        'solutions': [
            'How many refugees returned home in 2024?',
            'What are the main destination countries for resettlement?',
            'How many people were naturalized last year?',
            'What is the trend in durable solutions over time?',
            'Which countries have the highest return rates?'
        ]
    }
    
    questions: list[str] = []
    
    if topic and topic in suggested_questions:
        questions = suggested_questions[topic][:limit]
    elif data_type:
        # Map data types to topics
        type_to_topic = {
            'population': 'refugees',
            'demographics': 'demographics',
            'rsd': 'asylum',
            'solutions': 'solutions'
        }
        topic = type_to_topic.get(data_type, 'refugees')
        questions = suggested_questions.get(topic, [])[:limit]
    else:
        # Return a sample from each category
        for q_list in suggested_questions.values():
            questions.extend(q_list[:1])
        questions = questions[:limit]
    
    return {
        'topic': topic or data_type or 'general',
        'questions': questions,
        'count': len(questions),
        'metadata': {
            'source': 'UNHCR Question Suggester',
            'limit': limit
        }
    }
