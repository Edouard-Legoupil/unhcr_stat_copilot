from __future__ import annotations

import json
import logging
import os
import time

import httpx
from dotenv import load_dotenv

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

# Azure OpenAI client is REQUIRED - fail if not configured
if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    raise RuntimeError(
        "Azure OpenAI is required. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in your environment."
    )


# Custom Azure OpenAI client for Responses API
# Azure OpenAI Responses API uses /responses endpoint instead of /deployments/{name}/chat/completions
base_url = f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai"


class MockResponse:
    """Mock response object that mimics AzureOpenAI chat completion response."""
    def __init__(self, content: str):
        self.choices = [MockChoice(content)]


class MockChoice:
    """Mock choice object."""
    def __init__(self, content: str):
        self.message = MockMessage(content)


class MockMessage:
    """Mock message object."""
    def __init__(self, content: str):
        self.content = content


class MockCompletions:
    """Mock completions object with create method."""
    def __init__(self, client):
        self.client = client
    
    async def create(self, **kwargs):
        """Handle the create call by forwarding to _responses_create"""
        return await self.client._responses_create(**kwargs)


class MockChat:
    """Mock chat object with completions attribute."""
    def __init__(self, client):
        self.completions = MockCompletions(client)


class AzureOpenAIResponsesClient:
    """
    Custom Azure OpenAI client that uses the Responses API endpoint.
    This class mimics the AsyncAzureOpenAI interface but uses /responses endpoint.
    """
    
    def __init__(self, api_key, azure_endpoint, api_version):
        self.api_key = api_key
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self.chat = MockChat(self)
    
    async def _responses_create(
        self,
        model: str,
        messages: list | None = None,
        input_param: list | str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_completion_tokens: int | None = None,
        response_format: dict | None = None,
        text_format: dict | None = None,
        **kwargs
    ) -> MockResponse:
        """
        Internal implementation for the Responses API.
        
        The Azure OpenAI Responses API uses different parameter names:
        - 'messages' -> 'input' (required parameter change)
        - 'response_format' -> 'text.format' (required parameter change)
        
        This method handles backward compatibility by accepting both old and new names.
        """
        url = f"{base_url}/responses?api-version={self.api_version}"
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Build the request payload for Responses API
        payload = {
            "model": model,
        }
        
        # Handle input parameter - Responses API uses 'input' instead of 'messages'
        if input_param is not None:
            payload["input"] = input_param
        elif messages is not None:
            # Backward compatibility: convert messages to input
            payload["input"] = messages
        
        # Handle text format - Responses API uses 'text.format' instead of 'response_format'
        if text_format is not None:
            if "text" not in payload:
                payload["text"] = {}
            payload["text"]["format"] = text_format.get("type", "text")
        elif response_format is not None:
            # Backward compatibility: convert response_format to text.format
            if "text" not in payload:
                payload["text"] = {}
            payload["text"]["format"] = response_format.get("type", "text")
        
        # Add optional parameters
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        elif max_completion_tokens is not None:
            payload["max_tokens"] = max_completion_tokens
        
        # Add any additional kwargs
        for key, value in kwargs.items():
            if value is not None:
                payload[key] = value
        
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                
                # Extract content from response
                content = ""
                if "choices" in response_data:
                    content = response_data["choices"][0]["message"]["content"]
                elif "output" in response_data:
                    content = response_data["output"]
                else:
                    content = response_data.get("text", "") or response_data.get("content", "")
                    if not content:
                        for key, value in response_data.items():
                            if isinstance(value, str) and value:
                                content = value
                                break
                
                return MockResponse(content)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Azure OpenAI Responses API error: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Azure OpenAI API error: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            logger.error(f"Azure OpenAI Responses API request failed: {e}")
            raise RuntimeError(f"Failed to call Azure OpenAI: {e}") from e


# Create the client using our custom class
try:
    client = AzureOpenAIResponsesClient(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=OPENAI_API_VERSION,
    )
    logger.info("Azure OpenAI client (Responses API) initialized successfully")
except Exception as e:
    raise RuntimeError(f"Failed to initialize Azure OpenAI client: {e}") from e

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
        raise RuntimeError(f"Failed to get MCP guidance: {e}") from e


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
        raise RuntimeError(f"Failed to get MCP examples: {e}") from e


# =====================================================
# Tool Discovery
# =====================================================




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
        raise RuntimeError("No valid MCP tools available - MCP server may be down or misconfigured")

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
        input_param=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": question
            }
        ],
        text_format={
            "type": "json_object"
        }
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
        input_param=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ],
        text_format={
            "type": "json_object"
        }
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

        logger.error(
            "Invalid tool selected: %s",
            tool
        )
        raise ValueError(f"Invalid tool: {tool}. Valid tools: {valid_tools}")

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
        input_param=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        text_format={
            "type": "json_object"
        }
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
        extracted_params = await extract_question_parameters(question)
        
        # Add extracted parameters to the selection
        selection["parameters"] = extracted_params
        
        logger.info(
            "Extracted parameters from question: %s",
            extracted_params
        )

        return selection

    except Exception as e:

        logger.exception(e)
        raise RuntimeError(f"Tool selection failed: {e}") from e


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
    data: dict,
    audience: str | None = None,
    document_type: str | None = None,
    tone: str | None = None,
    length_config: dict | None = None,
    structure: list[str] | None = None
) -> str:
    """
    Use the Azure OpenAI client to generate an analytical story 
    based on the user's question and the data retrieved from the API.
    
    Args:
        question: The user's question
        data: The data retrieved from the API
        audience: Target audience for the story
        document_type: Type of document being generated
        tone: Writing tone for the story
        length_config: Length configuration (wordRange, readingTime, density)
        structure: Structure/sections for the story
    """
    try:
        data_str = json.dumps(data, indent=2)
        # Prevent context window overflow by truncating if necessary
        if len(data_str) > 20000:
            data_str = data_str[:20000] + "\n...[data truncated]..."
        
        # Build system prompt based on configuration
        system_prompt_parts = [
            "You are an expert UNHCR data analyst and storyteller.",
            "Your job is to analyze data returned by the UNHCR API and write a compelling, "
            "analytical narrative responding to the user's question.",
            "Focus on key trends, demographic breakdowns, or significant shifts in the data.",
            "Format the output as clean Markdown."
        ]
        
        # Add tone instructions if provided
        if tone:
            system_prompt_parts.append(f"Write with a {tone} tone.")
        
        # Add length instructions if provided
        if length_config:
            word_range = length_config.get("wordRange", "1200-3000")
            reading_time = length_config.get("readingTime", "6-15 min")
            density = length_config.get("density", "medium")
            system_prompt_parts.append(f"Target length: {word_range} words ({reading_time}). Density: {density}.")
        
        # Add structure instructions if provided
        if structure:
            structure_str = " → ".join(structure)
            system_prompt_parts.append(f"Follow this structure: {structure_str}.")
        
        system_prompt = " ".join(system_prompt_parts)
        
        user_prompt = f"User Question: {question}\n\nUNHCR API Data:\n{data_str}\n\nPlease write a detailed analytical story based on this data."

        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            input_param=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.exception("Failed to generate story from data: %s", e)
        raise RuntimeError(f"Failed to generate story from data: {e}") from e