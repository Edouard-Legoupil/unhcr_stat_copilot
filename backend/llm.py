from __future__ import annotations

import json
import logging
import os
import time

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

from backend.mcp_bridge import call_tool

# =====================================================
# Environment
# =====================================================

load_dotenv()

logger = logging.getLogger(__name__)

AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT"
)

AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY"
)

AZURE_OPENAI_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT",
    "gpt-4.1"
)

OPENAI_API_VERSION = os.getenv(
    "OPENAI_API_VERSION",
    "2024-10-21"
)

# Azure OpenAI client is optional - only initialize if configured
client = None
if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY:
    try:
        client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=OPENAI_API_VERSION,
        )
        logger.info("Azure OpenAI client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Azure OpenAI client: {e}")
        client = None
else:
    logger.info("Azure OpenAI not configured - AI features will be limited")

# =====================================================
# Cache
# =====================================================

CACHE_TTL = 3600

_guidance_cache = None
_guidance_cache_time = 0

_examples_cache = None
_examples_cache_time = 0

# =====================================================
# MCP Metadata
# =====================================================


async def get_mcp_guidance() -> dict:

    global _guidance_cache
    global _guidance_cache_time

    if (
        _guidance_cache is not None
        and (
            time.time() -
            _guidance_cache_time
        ) < CACHE_TTL
    ):
        return _guidance_cache

    try:

        guidance = await call_tool(
            "get_usage_guidance",
            {}
        )

        _guidance_cache = guidance
        _guidance_cache_time = time.time()

        return guidance

    except Exception as e:

        logger.exception(e)

        return {}


async def get_mcp_examples() -> dict:

    global _examples_cache
    global _examples_cache_time

    if (
        _examples_cache is not None
        and (
            time.time() -
            _examples_cache_time
        ) < CACHE_TTL
    ):
        return _examples_cache

    try:

        examples = await call_tool(
            "get_suggested_questions",
            {}
        )

        _examples_cache = examples
        _examples_cache_time = time.time()

        return examples

    except Exception as e:

        logger.exception(e)

        return {}


# =====================================================
# Tool Discovery
# =====================================================

DEFAULT_TOOLS = {
    "get_population_data",
    "get_demographics_data",
    "get_rsd_applications",
    "get_rsd_decisions",
    "get_solutions",
    "get_country_key_figures",
    "get_population_trends",
    "get_demographic_breakdown",
    "extract_visualization_structure",
    "analyze_data_statistics",
    "generate_visualization_description",
    "generate_ai_data_story",
    "get_usage_guidance",
    "get_suggested_questions",
    "apply_analysis_guardrails",
    "create_quarto_notebook",
}


async def get_valid_tools() -> set:

    guidance = await get_mcp_guidance()

    tools = set()

    if isinstance(guidance, dict):

        categories = guidance.get(
            "categories",
            {}
        )

        for category in categories.values():

            if not isinstance(
                category,
                dict
            ):
                continue

            for tool in category.get(
                "tools",
                []
            ):
                tools.add(tool)

    if not tools:
        tools = DEFAULT_TOOLS

    return tools


# =====================================================
# Prompt Builder
# =====================================================

async def build_system_prompt() -> str:

    guidance = await get_mcp_guidance()

    examples = await get_mcp_examples()

    return f"""
You are a senior UNHCR data analyst.

Your job is to select the best MCP tool.

AVAILABLE MCP CAPABILITIES

{json.dumps(guidance, indent=2)}

EXAMPLE QUESTIONS

{json.dumps(examples, indent=2)}

Convert country names into ISO3.

Examples:

France -> FRA
Switzerland -> CHE
Germany -> DEU
Uganda -> UGA
Chad -> TCD
Kenya -> KEN
Sudan -> SDN
South Sudan -> SSD
Colombia -> COL
Syria -> SYR

Return ONLY JSON.

Format:

{{
    "tool": "tool_name",
    "arguments": {{}}
}}

No markdown.
No explanations.
Only JSON.
"""


# =====================================================
# Classification
# =====================================================

async def classify_question(
    question: str
) -> dict:

    prompt = """
Classify this question.

Possible values:

population
demographics
trends
rsd
solutions
storytelling
guidance
reporting

Return JSON:

{
  "category": ""
}
"""

    response = await client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=1,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    return json.loads(
        response.choices[0]
        .message.content
    )


# =====================================================
# Tool Selection
# =====================================================

async def select_tool_from_prompt(
    question: str
) -> dict:

    system_prompt = (
        await build_system_prompt()
    )

    response = await client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=1,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    return json.loads(
        response.choices[0]
        .message.content
    )


# =====================================================
# Validation
# =====================================================

async def validate_tool_selection(
    selection: dict
) -> dict:

    valid_tools = (
        await get_valid_tools()
    )

    tool = selection.get("tool")

    if tool not in valid_tools:

        logger.warning(
            "Invalid tool selected: %s",
            tool
        )

        return {
            "tool":
                "get_usage_guidance",
            "arguments": {}
        }

    return selection


# =====================================================
# Retry
# =====================================================

async def retry_tool_selection(
    question: str
) -> dict:

    valid_tools = list(
        await get_valid_tools()
    )

    prompt = f"""
Choose ONE tool.

Valid tools:

{json.dumps(valid_tools)}

Question:

{question}

Return JSON:

{{
  "tool": "",
  "arguments": {{}}
}}
"""

    response = await client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=1,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return json.loads(
        response.choices[0]
        .message.content
    )


# =====================================================
# Main Entry Point
# =====================================================

async def safe_tool_selection(
    question: str
) -> dict:

    try:

        category = (
            await classify_question(
                question
            )
        )

        logger.info(
            "Question category=%s",
            category.get(
                "category"
            )
        )

        selection = (
            await select_tool_from_prompt(
                question
            )
        )

        selection = (
            await validate_tool_selection(
                selection
            )
        )

        if (
            selection["tool"]
            == "get_usage_guidance"
        ):

            selection = (
                await retry_tool_selection(
                    question
                )
            )

            selection = (
                await validate_tool_selection(
                    selection
                )
            )

        # Extract parameters from the question to include in the response
        from backend.question_parser import extract_question_parameters
        extracted_params = extract_question_parameters(question)
        
        # Add extracted parameters to the selection
        selection["parameters"] = extracted_params
        
        logger.info(
            "Extracted parameters from question: %s",
            extracted_params
        )

        return selection

    except Exception as e:

        logger.exception(e)

        return {
            "tool":
                "get_usage_guidance",
            "arguments": {},
            "parameters": {}
        }


# =====================================================
# Debug Helper
# =====================================================

async def explain_tool_choice(
    question: str
) -> dict:

    classification = (
        await classify_question(
            question
        )
    )

    selection = (
        await safe_tool_selection(
            question
        )
    )

    return {
        "question":
            question,
        "classification":
            classification,
        "selection":
            selection
    }


# =====================================================
# Content Generation
# =====================================================

async def generate_story_from_data(
    question: str,
    data: dict
) -> str:
    """
    Use the Azure OpenAI client to generate an analytical story 
    based on the user's question and the data retrieved from the API.
    """
    try:
        data_str = json.dumps(data, indent=2)
        # Prevent context window overflow by truncating if necessary
        if len(data_str) > 20000:
            data_str = data_str[:20000] + "\n...[data truncated]..."
            
        system_prompt = (
            "You are an expert UNHCR data analyst and storyteller. "
            "Your job is to analyze data returned by the UNHCR API and write a compelling, "
            "analytical narrative responding to the user's question. "
            "Focus on key trends, demographic breakdowns, or significant shifts in the data. "
            "Format the output as clean Markdown."
        )
        
        user_prompt = f"User Question: {question}\n\nUNHCR API Data:\n{data_str}\n\nPlease write a detailed analytical story based on this data."

        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.exception("Failed to generate story from data: %s", e)
        error_type = type(e).__name__
        
        # Provide more specific error messages based on error type
        if "AuthenticationError" in error_type or "Authentication" in str(e):
            return "Could not generate story due to authentication error. Please check your API credentials."
        elif "RateLimitError" in error_type or "rate limit" in str(e).lower():
            return "Could not generate story due to API rate limit. Please try again later."
        elif "ConnectionError" in error_type or "connection" in str(e).lower():
            return "Could not generate story due to network connection error. Please check your internet connection."
        elif "Timeout" in error_type or "timeout" in str(e).lower():
            return "Could not generate story due to request timeout. The AI service is taking too long to respond."
        elif "APIError" in error_type or "api_error" in str(e).lower():
            return "Could not generate story due to AI service error. Please try again later."
        else:
            return f"Could not generate story due to an error: {error_type}. Please try again or contact support."