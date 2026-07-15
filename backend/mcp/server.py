#!/usr/bin/env python3
"""
UNHCR Forcibly Displaced Populations MCP Server

This MCP server provides access to various UNHCR endpoints through the Model Context Protocol.
It allows querying data around forcibly displaced persons by country of origin, country of asylum,
and year(s), as well as provide data on Refugee Status Determination (RSD) Applications and
Refugee Status Determination (RSD) decisions.

API Endpoint: https://api.unhcr.org/population/v1/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional, Union

from mcp.server.fastmcp import FastMCP
from smithery.decorators import smithery

# Import from common module
from backend.mcp.common import (
    DEFAULT_RAG_DEVICE,
    DEFAULT_RAG_EMBED_MODEL,
    DEFAULT_RAG_FETCH_K,
    DEFAULT_RAG_RERANK_MODEL,
    DEFAULT_RAG_TOP_K,
    UNHCRAPIClient,
    UNHCRVectorRetriever,
    RetrievedChunk,
    summarize_retrieved_context_for_story,
    _get_population_color,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Configure file-based logging for persistence
# Log configuration is controlled by environment variables:
# - MCP_LOG_FILE: Path to MCP log file (set in start.sh/boot.sh)
# - LOG_LEVEL: Log level (default: INFO)
# - LOG_ENABLED: Enable/disable file logging (default: true)
from backend.mcp.observability.logging import configure_logging

log_enabled = os.getenv("LOG_ENABLED", "true").lower() == "true"
if log_enabled:
    configure_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("MCP_LOG_FILE", "logs/unhcr_mcp_server.log")
    )

logger = logging.getLogger(__name__)


@smithery.server()
def create_server() -> FastMCP:
    """
    Create and return a FastMCP server instance.

    Returns:
        Configured FastMCP server
    """
    # Restrict allowed hosts and require authentication for MCP server
    # Default to localhost; override via ALLOWED_HOSTS env var (comma-separated)
    allowed = os.getenv("ALLOWED_HOSTS", "localhost").split(",")
    os.environ["ALLOWED_HOSTS"] = ",".join(allowed)

    # Initialize the server
    server = FastMCP(
        name="UNHCR Forcibly Displaced Populations MCP Server",
        instructions=(
            "Provides UNHCR population data tools and data-story generation. "
            "Enforces host-based origin checks and requires API key auth for all requests. "
            "Can optionally enrich data stories with contextual evidence from "
            "local UNHCR Global Trends and Mid-Year Trends reports."
        ),
    )
    # TODO: enforce API-key authentication via server middleware or configuration

    # Import tools from the tools package
    # These will be registered with the server
    from backend.mcp.tools import (
        retrieve_report_context_tool,
        get_population_data_tool,
        get_demographics_data_tool,
        get_rsd_applications_tool,
        get_rsd_decisions_tool,
        get_solutions_tool,
        get_country_key_figures_tool,
        get_population_trends_tool,
        get_demographic_breakdown_tool,
        extract_visualization_structure_tool,
        analyze_data_statistics_tool,
        generate_visualization_description_tool,
        get_usage_guidance_tool,
        get_suggested_questions_tool,
        apply_analysis_guardrails_tool,
        create_quarto_notebook_tool,
        safe_tool_selection_tool,
        get_data_for_story_tool,
        generate_analytical_story_tool,
    )

    rag_retriever = UNHCRVectorRetriever()
    api_client = UNHCRAPIClient()

    # Register all tools with the server
    # Each tool function will receive the necessary dependencies
    
    @server.tool(
        name="retrieve_report_context",
        description=(
            "Retrieve relevant contextual excerpts from the local UNHCR report vector store. "
            "Use this to support data stories, methodology explanations, and source-grounded analysis."
        ),
    )
    def retrieve_report_context_wrapper(
        request: str,
        top_k: int = DEFAULT_RAG_TOP_K,
        fetch_k: int = DEFAULT_RAG_FETCH_K,
        year: Optional[str] = None,
        report_type: Optional[str] = None,
        section_contains: Optional[str] = None,
        exclude_figures_tables: bool = False,
        rerank: bool = False,
    ) -> dict[str, Any]:
        return retrieve_report_context_tool(
            rag_retriever, request, top_k, fetch_k, year, report_type, 
            section_contains, exclude_figures_tables, rerank
        )

    @server.tool(
        name="get_population_data",
        description=(
            "Retrieve forcibly displaced population statistics from UNHCR. "
            "Use this tool when asked about refugee numbers, asylum seekers, stateless persons, "
            "or other populations of concern by country and year."
        ),
    )
    def get_population_data_wrapper(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        return get_population_data_tool(api_client, coo, coa, year, coo_all, coa_all)

    @server.tool(
        name="get_demographics_data",
        description=(
            "Retrieve age and sex breakdown data for forcibly displaced populations. "
            "Use this tool when asked about demographic composition, gender distribution, "
            "or age groups of refugees and other populations of concern."
        ),
    )
    def get_demographics_data_wrapper(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
        pop_type: bool = False,
    ) -> dict[str, Any]:
        return get_demographics_data_tool(api_client, coo, coa, year, coo_all, coa_all, pop_type)

    @server.tool(
        name="get_rsd_applications",
        description=(
            "Retrieve Refugee Status Determination (RSD) application statistics. "
            "Use this tool when asked about asylum applications, claims, or requests for refugee status "
            "by country, origin, or year."
        ),
    )
    def get_rsd_applications_wrapper(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        return get_rsd_applications_tool(api_client, coo, coa, year, coo_all, coa_all)

    @server.tool(
        name="get_rsd_decisions",
        description=(
            "Retrieve Refugee Status Determination (RSD) decision outcomes. "
            "Use this tool when asked about approved/rejected asylum cases, recognition rates, "
            "or refugee status determination results by country and year."
        ),
    )
    def get_rsd_decisions_wrapper(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        return get_rsd_decisions_tool(api_client, coo, coa, year, coo_all, coa_all)

    @server.tool(
        name="get_solutions",
        description=(
            "Retrieve durable solutions data including refugee returnees, resettlement, "
            "naturalization, and IDP returns. Use this tool when asked about solutions "
            "to displacement, voluntary repatriation, or integration outcomes."
        ),
    )
    def get_solutions_wrapper(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        return get_solutions_tool(api_client, coo, coa, year, coo_all, coa_all)

    @server.tool(
        name="get_country_key_figures",
        description=(
            "Retrieve formatted key statistics and summaries for specific countries. "
            "Use this tool when asked for country profiles, overview statistics, "
            "or formatted summaries of displacement situations."
        ),
    )
    def get_country_key_figures_wrapper(
        coa: str | None = None,
        coo: str | None = None,
        year: str | int | None = None,
        population_types: list[str] | None = None
    ) -> dict[str, Any]:
        return get_country_key_figures_tool(api_client, coa, coo, year, population_types, _get_population_color)

    @server.tool(
        name="get_population_trends",
        description=(
            "Retrieve time series data showing population changes over multiple years. "
            "Use this tool when asked about trends, historical changes, or comparisons "
            "across different time periods."
        ),
    )
    def get_population_trends_wrapper(
        coa: str | None = None,
        coo: str | None = None,
        years: str | None = None,
        population_types: list[str] | None = None
    ) -> dict[str, Any]:
        return get_population_trends_tool(api_client, coa, coo, years, population_types)

    @server.tool(
        name="get_demographic_breakdown",
        description=(
            "Retrieve detailed age and sex distribution for specific population types. "
            "Use this tool when asked for granular demographic analysis, age pyramids, "
            "or gender breakdowns of refugee populations."
        ),
    )
    def get_demographic_breakdown_wrapper(
        coa: str | None = None,
        coo: str | None = None,
        year: str | int | None = None,
        population_type: str | None = None
    ) -> dict[str, Any]:
        return get_demographic_breakdown_tool(api_client, coa, coo, year, population_type)

    @server.tool(
        name="extract_visualization_structure",
        description=(
            "Extract and structure visualization metadata for AI-generated reports. "
            "Use this tool when asked to create charts, graphs, or visual representations "
            "of data for reporting purposes."
        ),
    )
    def extract_visualization_structure_wrapper(
        visualization_type: str,
        title: str | None = None,
        subtitle: str | None = None,
        x_axis_label: str | None = None,
        y_axis_label: str | None = None,
        x_axis_range: list[float] | None = None,
        y_axis_range: list[float] | None = None,
        legend_items: list[str] | None = None,
        geometric_layers: list[str] | None = None
    ) -> dict[str, Any]:
        return extract_visualization_structure_tool(
            visualization_type, title, subtitle, x_axis_label, y_axis_label,
            x_axis_range, y_axis_range, legend_items, geometric_layers
        )

    @server.tool(
        name="analyze_data_statistics",
        description=(
            "Perform statistical analysis on datasets including descriptive statistics, "
            "correlations, and distributions. Use this tool when asked for data analysis, "
            "statistical summaries, or insights from numerical data."
        ),
    )
    def analyze_data_statistics_wrapper(
        data: list[dict[str, Any]],
        numeric_columns: list[str],
        categorical_columns: list[str] | None = None,
        correlation_columns: list[str] | None = None
    ) -> dict[str, Any]:
        return analyze_data_statistics_tool(data, numeric_columns, categorical_columns, correlation_columns)

    @server.tool(
        name="generate_visualization_description",
        description=(
            "Generate AI-powered descriptions and interpretations for visualizations. "
            "Use this tool when asked to explain charts, provide insights from graphs, "
            "or create narrative descriptions of data visualizations."
        ),
    )
    async def generate_visualization_description_wrapper(
        structure: dict[str, Any],
        statistics: dict[str, Any] | None = None,
        description_type: str = "both",
        max_length: int = 300,
        focus_areas: list[str] | None = None
    ) -> dict[str, Any]:
        return await generate_visualization_description_tool(
            structure, statistics, description_type, max_length, focus_areas
        )



    @server.tool(
        name="get_usage_guidance",
        description=(
            "Get usage guidance, examples, and best practices for UNHCR MCP tools. "
            "Use this tool when asked how to use the system, what tools are available, "
            "or for help with specific tool usage."
        ),
    )
    def get_usage_guidance_wrapper(
        tool_category: str | None = None,
        specific_tool: str | None = None
    ) -> dict[str, Any]:
        return get_usage_guidance_tool(tool_category, specific_tool)

    @server.tool(
        name="get_suggested_questions",
        description=(
            "Get suggested questions and query examples based on topics or data types. "
            "Use this tool when users need help formulating questions or don't know what to ask."
        ),
    )
    def get_suggested_questions_wrapper(
        topic: str | None = None,
        data_type: str | None = None,
        limit: int = 5
    ) -> dict[str, Any]:
        return get_suggested_questions_tool(topic, data_type, limit)

    @server.tool(
        name="apply_analysis_guardrails",
        description=(
            "Apply UNHCR methodology guardrails to ensure analyses follow international standards. "
            "Use this tool to validate analysis requests, check compliance with statistical standards, "
            "and ensure proper interpretation of UNHCR data."
        ),
    )
    def apply_analysis_guardrails_wrapper(
        analysis_request: dict[str, Any],
        population_type: str | None = None,
        country_iso: str | None = None,
        year: str | int | None = None,
        detailed_report: bool = False
    ) -> dict[str, Any]:
        return apply_analysis_guardrails_tool(
            analysis_request, population_type, country_iso, year, detailed_report
        )

    @server.tool(
        name="create_quarto_notebook",
        description=(
            "Create Quarto notebooks (.qmd files) from data stories for reproducible reporting. "
            "Use this tool when asked to generate reports, create notebooks, or export analysis "
            "in a reproducible format."
        ),
    )
    async def create_quarto_notebook_wrapper(
        story_content: str,
        output_path: str | None = None,
        title: str | None = None,
        author: str | None = None,
        date: str | None = None,
        include_code_cells: bool = False,
        use_unhcr_theme: bool = True,
        use_unhcr_style: bool = True,
        original_query: str | None = None,
        metadata: dict[str, Any] | None = None,
        data: Any | None = None
    ) -> dict[str, Any]:
        return await create_quarto_notebook_tool(
            story_content, output_path, title, author, date, include_code_cells,
            use_unhcr_theme, use_unhcr_style, original_query, metadata, data
        )

    @server.tool(
        name="safe_tool_selection",
        description=(
            "Safely select the appropriate tool for a given question by analyzing its content. "
            "Use this tool to determine which UNHCR data tool should be used for a specific query."
        ),
    )
    async def safe_tool_selection_wrapper(question: str) -> dict[str, Any]:
        return await safe_tool_selection_tool(question)

    @server.tool(
        name="get_data_for_story",
        description=(
            "Get appropriate data for story generation based on question analysis. "
            "Use this tool to retrieve the right data for creating data-driven stories and reports."
        ),
    )
    async def get_data_for_story_wrapper(
        question: str,
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        years: str | None = None,
        population_types: list[str] | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
        audience: str | None = None,
        document_type: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        population_type: str | None = None,
        timespan: str | None = None
    ) -> dict[str, Any]:
        return await get_data_for_story_tool(
            api_client, question, coo, coa, year, years, population_types,
            coo_all, coa_all, audience, document_type, origin, destination,
            population_type, timespan
        )

    @server.tool(
        name="generate_analytical_story",
        description=(
            "Generate analytical stories and narratives from UNHCR data, optionally enriched "
            "with relevant context retrieved from local UNHCR statistical reports. "
            "Use this tool when asked to create reports, stories, or narratives based on data analysis."
        ),
    )
    async def generate_analytical_story_wrapper(
        result: dict | None = None,
        data: dict | None = None,
        question: str = "",
        audience: str | None = None,
        document_type: str | None = None,
        analysis_config: dict | None = None,
        # RAG parameters - enabled by default
        use_rag: bool = True,
        rag_top_k: int = DEFAULT_RAG_TOP_K,
        rag_fetch_k: int = DEFAULT_RAG_FETCH_K,
        rag_rerank: bool = False,
        rag_year: str | None = None,
        rag_report_type: str | None = None,
        rag_section_contains: str | None = None,
        rag_exclude_figures_tables: bool = False,
        context: str | None = None,
    ) -> dict[str, Any]:
        return await generate_analytical_story_tool(
            result=result,
            data=data,
            question=question,
            audience=audience,
            document_type=document_type,
            analysis_config=analysis_config,
            use_rag=use_rag,
            rag_retriever=rag_retriever if use_rag else None,
            rag_top_k=rag_top_k,
            rag_fetch_k=rag_fetch_k,
            rag_rerank=rag_rerank,
            rag_year=rag_year,
            rag_report_type=rag_report_type,
            rag_section_contains=rag_section_contains,
            rag_exclude_figures_tables=rag_exclude_figures_tables,
            context=context,
        )

    @server.tool(
        name="run_enhanced_analysis",
        description=(
            "Run the complete enhanced analysis pipeline with statistical analysis, "
            "compliance validation, visualization structure extraction, and description generation. "
            "Use this for comprehensive, in-depth analysis requests that require rich insights."
        ),
    )
    async def run_enhanced_analysis_wrapper(
        question: str,
        data: dict[str, Any],
        audience: str | None = None,
        document_type: str | None = None,
        analysis_config: dict | None = None,
        use_rag: bool = False,
    ) -> dict[str, Any]:
        if use_rag:
            return await run_enhanced_analysis_pipeline(
                question, data, audience, document_type, analysis_config,
                use_rag=True, rag_retriever=rag_retriever
            )
        else:
            return await run_enhanced_analysis_pipeline(
                question, data, audience, document_type, analysis_config,
                use_rag=False
            )

    @server.tool(
        name="run_conditional_analysis",
        description=(
            "Run conditional analysis pipeline that auto-detects whether to use enhanced "
            "(for complex queries) or simple (for basic queries) workflow. "
            "Complex queries contain keywords like 'analyze', 'trends', 'correlation', etc."
        ),
    )
    async def run_conditional_analysis_wrapper(
        question: str,
        data: dict[str, Any],
        audience: str | None = None,
        document_type: str | None = None,
        analysis_config: dict | None = None,
        use_enhanced: bool | None = None,
    ) -> dict[str, Any]:
        return await run_conditional_analysis_pipeline(
            question, data, audience, document_type, analysis_config,
            use_enhanced=use_enhanced, rag_retriever=rag_retriever
        )

    @server.tool(
        name="full_analysis_workflow",
        description=(
            "Complete end-to-end analysis workflow: question → data → enrichment → story → notebook. "
            "This is the highest-level tool that orchestrates all steps of analysis. "
            "Use this for comprehensive analysis requests. "
            "Optionally uses RAG (Retrieval-Augmented Generation) for enriched stories."
        ),
    )
    async def full_analysis_workflow_wrapper(
        question: str,
        origin: str | None = None,
        destination: str | None = None,
        topic: str | None = None,
        timespan: str | None = None,
        year: str | int | None = None,
        years: str | None = None,
        population_types: list[str] | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
        audience: str | None = None,
        document_type: str | None = None,
        style: str | None = None,
        use_enhanced: bool = True,
        use_rag: bool = False,
        include_notebook: bool = True,
        include_html: bool = True,
        include_pdf: bool = True,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        return await full_analysis_workflow_tool(
            question, origin, destination, topic, timespan, year, years,
            population_types, coo_all, coa_all, audience, document_type, style,
            use_enhanced, use_rag, rag_retriever if use_rag else None,
            include_notebook, include_html, include_pdf, output_path
        )

    @server.tool(
        name="quick_analysis",
        description=(
            "Quick analysis workflow: question → data → simple story (no notebook). "
            "Use this for lightweight, fast analysis requests that don't require "
            "notebook generation."
        ),
    )
    async def quick_analysis_wrapper(
        question: str,
        audience: str | None = None,
        document_type: str | None = None,
    ) -> dict[str, Any]:
        return await quick_analysis_tool(question, audience, document_type)

    @server.tool(
        name="compare_analysis",
        description=(
            "Comparative analysis workflow: Run the same analysis for multiple scenarios. "
            "Use this when asked to compare data across different countries, years, "
            "or other dimensions."
        ),
    )
    async def compare_analysis_wrapper(
        question_template: str,
        comparisons: list[dict[str, Any]],
        audience: str | None = None,
    ) -> dict[str, Any]:
        return await compare_analysis_tool(question_template, comparisons, audience)

    return server


def main() -> None:
    """
    Main entry point for the MCP server.
    """
    logger.info("Starting UNHCR Statistics Copilot MCP Server")
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
