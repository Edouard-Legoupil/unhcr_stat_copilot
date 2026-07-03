#!/usr/bin/env python3
"""
Integration test for LLM and MCP server functionality.

This test assumes:
1. Azure OpenAI is configured (via .env file or environment variables)
2. MCP server is running on localhost:8000
3. All MCP tools are available

These tests verify that the LLM and MCP integration works correctly
when the required services are available.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_llm_configuration():
    """Test that LLM is properly configured with Azure OpenAI."""
    print("\n🧪 Test 1: LLM configuration...")
    
    try:
        from backend import llm
        from openai import AsyncAzureOpenAI
        
        # Verify client exists and is correct type
        assert llm.client is not None, "LLM client should be initialized"
        assert isinstance(llm.client, AsyncAzureOpenAI), "Client should be AsyncAzureOpenAI"
        
        # Verify configuration
        assert llm.AZURE_OPENAI_ENDPOINT is not None, "Endpoint should be configured"
        assert llm.AZURE_OPENAI_API_KEY is not None, "API key should be configured"
        assert llm.AZURE_OPENAI_DEPLOYMENT is not None, "Deployment should be configured"
        assert llm.OPENAI_API_VERSION is not None, "API version should be configured"
        
        print(f"  ✅ LLM client: {type(llm.client).__name__}")
        print(f"  ✅ Endpoint: {llm.AZURE_OPENAI_ENDPOINT}")
        print(f"  ✅ Deployment: {llm.AZURE_OPENAI_DEPLOYMENT}")
        print(f"  ✅ API Version: {llm.OPENAI_API_VERSION}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_server_connection():
    """Test connection to MCP server running on localhost."""
    print("\n🧪 Test 2: MCP server connection...")
    
    try:
        from backend.llm import get_mcp_guidance, get_mcp_examples, get_valid_tools
        
        # Test MCP guidance (assumes MCP server is running)
        guidance = await get_mcp_guidance()
        assert isinstance(guidance, dict), "Guidance should be a dictionary"
        assert guidance, "Guidance should not be empty"
        print(f"  ✅ MCP guidance retrieved successfully")
        
        # Test MCP examples (assumes MCP server is running)
        examples = await get_mcp_examples()
        assert isinstance(examples, dict), "Examples should be a dictionary"
        assert examples, "Examples should not be empty"
        print(f"  ✅ MCP examples retrieved successfully")
        
        # Test valid tools (assumes MCP server is running)
        tools = await get_valid_tools()
        assert isinstance(tools, set), "Tools should be a set"
        assert len(tools) > 0, "Should have at least one valid tool"
        print(f"  ✅ Valid tools retrieved: {len(tools)} tools")
        print(f"  ✅ Tools: {sorted(tools)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"  ℹ️  Note: This test requires MCP server to be running on localhost:8000")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_classification():
    """Test LLM classification functionality."""
    print("\n🧪 Test 3: LLM classification...")
    
    try:
        from backend.llm import classify_question
        
        # Test with a sample question
        question = "What are the refugee numbers in Turkey?"
        result = await classify_question(question)
        
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "category" in result, "Result should have category"
        assert result["category"] in ["population", "demographics", "trends", "rsd", "solutions", "storytelling", "guidance", "reporting"], "Invalid category"
        
        print(f"  ✅ Question classified: '{question}' -> {result['category']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"  ℹ️  Note: This test requires both Azure OpenAI and MCP server")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_selection():
    """Test LLM-based tool selection functionality."""
    print("\n🧪 Test 4: Tool selection...")
    
    try:
        from backend.llm import safe_tool_selection
        
        # Test with various questions
        test_questions = [
            "Refugees from Syria in 2024",
            "Demographic breakdown of refugees in Germany",
            "RSD decisions in France last year",
            "Solutions data for Colombia",
        ]
        
        for question in test_questions:
            result = await safe_tool_selection(question)
            assert isinstance(result, dict), f"Result for '{question}' should be a dictionary"
            assert "tool" in result, f"Result for '{question}' should have tool"
            assert "arguments" in result, f"Result for '{question}' should have arguments"
            print(f"  ✅ Question: '{question}' -> Tool: {result['tool']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"  ℹ️  Note: This test requires both Azure OpenAI and MCP server")
        import traceback
        traceback.print_exc()
        return False


async def test_direct_mcp_tool_calls():
    """Test direct MCP tool calls."""
    print("\n🧪 Test 5: Direct MCP tool calls...")
    
    try:
        from backend.mcp_bridge import call_tool
        
        # Test with a simple tool that doesn't require many parameters
        result = await call_tool("get_usage_guidance", {})
        assert isinstance(result, dict), "Result should be a dictionary"
        print(f"  ✅ get_usage_guidance called successfully")
        
        # Test suggested questions
        examples = await call_tool("get_suggested_questions", {"limit": 3})
        assert isinstance(examples, dict), "Examples should be a dictionary"
        print(f"  ✅ get_suggested_questions called successfully")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"  ℹ️  Note: This test requires MCP server to be running on localhost:8000")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_bridge_validation():
    """Test MCP bridge validation functionality."""
    print("\n🧪 Test 6: MCP bridge validation...")
    
    try:
        from backend.mcp_bridge import validate_tool_arguments, MCPValidationError
        
        # Test valid tool
        validate_tool_arguments("get_population_data", {"year": "2024"})
        print(f"  ✅ Valid tool arguments accepted")
        
        # Test invalid tool (should raise)
        try:
            validate_tool_arguments("unknown_tool", {})
            print(f"  ❌ Unknown tool was accepted")
            return False
        except MCPValidationError as e:
            print(f"  ✅ Unknown tool correctly rejected: {str(e)[:50]}...")
        
        # Test invalid year format (should raise)
        try:
            validate_tool_arguments("get_population_data", {"year": "invalid"})
            print(f"  ❌ Invalid year was accepted")
            return False
        except MCPValidationError as e:
            print(f"  ✅ Invalid year correctly rejected: {str(e)[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all LLM and MCP integration tests."""
    print("=" * 70)
    print("🚀 LLM & MCP Server Integration Tests")
    print("=" * 70)
    print("\nAssumptions:")
    print("  • Azure OpenAI is configured")
    print("  • MCP server is running on localhost:8000")
    print("  • All MCP tools are available")
    print("\nThese tests verify the integration works correctly.")
    
    results = []
    
    # Run synchronous tests
    results.append(("LLM configuration", test_llm_configuration()))
    
    # Run asynchronous tests
    results.append(("MCP server connection", await test_mcp_server_connection()))
    results.append(("LLM classification", await test_llm_classification()))
    results.append(("Tool selection", await test_tool_selection()))
    results.append(("Direct MCP tool calls", await test_direct_mcp_tool_calls()))
    results.append(("MCP bridge validation", await test_mcp_bridge_validation()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("\n🎯 LLM and MCP server integration is working correctly")
        print("🎯 Azure OpenAI is properly configured")
        print("🎯 MCP server is accessible and all tools are available")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("\n💡 Check that:")
        print("  • Azure OpenAI credentials are configured in .env")
        print("  • MCP server is running (localhost:8000)")
        print("  • All required Python packages are installed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)