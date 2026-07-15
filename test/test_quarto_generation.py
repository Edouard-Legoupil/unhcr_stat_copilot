#!/usr/bin/env python3
"""
Test script to verify Quarto generation fixes.

Tests:
1. Story content extraction from message objects
2. Metadata handling in templates
3. Code cell indentation
4. MCP tool integration
"""

import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_story_content_extraction():
    """Test that story content is properly extracted from various formats."""
    print("\n🧪 Test 1: Story content extraction...")
    
    from backend.mcp.tools.create_quarto_notebook import _extract_text_from_message
    
    # Test 1: Plain string
    result = _extract_text_from_message("Hello World")
    assert result == "Hello World", f"Expected 'Hello World', got '{result}'"
    print("  ✅ Plain string extraction works")
    
    # Test 2: Azure OpenAI message format (list with dict containing content list)
    azure_message = [{
        'id': 'msg_test',
        'type': 'message',
        'role': 'assistant',
        'content': [
            {'type': 'output_text', 'text': 'This is a test story'},
            {'type': 'output_text', 'text': 'This is another paragraph'}
        ]
    }]
    result = _extract_text_from_message(azure_message)
    assert 'This is a test story' in result, f"Expected story text in result, got: {result}"
    assert 'This is another paragraph' in result, f"Expected second paragraph in result, got: {result}"
    print("  ✅ Azure OpenAI message format extraction works")
    
    # Test 3: Nested dict with story key
    nested_dict = {'story': 'The actual story text'}
    result = _extract_text_from_message(nested_dict)
    assert result == 'The actual story text', f"Expected 'The actual story text', got '{result}'"
    print("  ✅ Nested dict extraction works")
    
    # Test 4: List of strings
    string_list = ['First paragraph', 'Second paragraph']
    result = _extract_text_from_message(string_list)
    assert 'First paragraph' in result, f"Expected first paragraph in result"
    assert 'Second paragraph' in result, f"Expected second paragraph in result"
    print("  ✅ List of strings extraction works")
    
    # Test 5: JSON string that looks like an array
    json_array = '[{"text": "extracted"}]'
    result = _extract_text_from_message(json_array)
    assert 'extracted' in result, f"Expected 'extracted' in result, got: {result}"
    print("  ✅ JSON array string extraction works")
    
    return True


def test_template_metadata_handling():
    """Test that metadata is properly handled in the template."""
    print("\n🧪 Test 2: Template metadata handling...")
    
    from pathlib import Path
    template_path = Path(__file__).parent.parent / 'backend' / 'templates' / 'quarto_notebook_interleaved.j2'
    
    # Check template exists
    assert template_path.exists(), f"Template not found at {template_path}"
    print("  ✅ Template file exists")
    
    # Check template contains metadata in YAML header format
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Check for metadata fields in YAML header
    assert 'unhcr_metadata:' in template_content, "Template should have unhcr_metadata in YAML"
    assert 'statistics:' in template_content, "Template should have statistics in YAML"
    assert 'guardrails:' in template_content, "Template should have guardrails in YAML"
    assert 'visualization_structure:' in template_content, "Template should have visualization_structure in YAML"
    print("  ✅ Template has metadata fields in YAML header")
    
    # Check that HTML comments are NOT used for metadata
    # (They should only be in the footer audit trail)
    assert '<!-- Audience:' not in template_content, "Template should not have audience in HTML comments"
    assert '<!-- Document Type:' not in template_content, "Template should not have document type in HTML comments"
    print("  ✅ Template does not use HTML comments for metadata")
    
    # Check for proper code cell handling
    assert '#| echo: false' in template_content, "Template should have echo: false for code cells"
    assert '#| fold: true' in template_content, "Template should have fold: true for metadata cells"
    print("  ✅ Template has proper code cell options")
    
    # Check for safe filter usage
    assert '| safe' in template_content, "Template should use | safe filter for story content"
    print("  ✅ Template uses | safe filter for story content")
    
    return True


def test_quarto_creation():
    """Test actual Quarto notebook creation."""
    print("\n🧪 Test 3: Quarto notebook creation...")
    
    import asyncio
    
    async def run_test():
        from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool
        
        # Test with simple story content
        story = "# Test Story\n\nThis is a test story about UNHCR data."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.qmd', delete=False) as f:
            temp_path = f.name
        
        try:
            result = await create_quarto_notebook_tool(
                story_content=story,
                output_path=temp_path,
                title="Test Notebook",
                include_code_cells=True,
                data=[{"year": 2023, "value": 100}]
            )
            
            assert result['status'] == 'success', f"Expected success, got: {result.get('status')}"
            print("  ✅ Quarto creation successful")
            
            # Check the generated file
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Verify story content is in the output
            assert 'Test Story' in content, "Story title should be in output"
            assert 'This is a test story about UNHCR data' in content, "Story content should be in output"
            print("  ✅ Story content properly included")
            
            # Verify metadata is in YAML header, not HTML comments
            assert 'unhcr_metadata:' in content, "Metadata should be in YAML header"
            assert '<!-- Audience:' not in content, "Metadata should not be in HTML comments"
            print("  ✅ Metadata in YAML header, not HTML comments")
            
            # Verify echo: false is used for code cells
            assert '#| echo: false' in content, "Code cells should use echo: false"
            print("  ✅ Code cells use echo: false")
            
        finally:
            # Cleanup
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return True
    
    return asyncio.run(run_test())


def test_quarto_creation_with_message_object():
    """Test Quarto creation with story content as a message object (the problematic case)."""
    print("\n🧪 Test 4: Quarto creation with message object story...")
    
    import asyncio
    
    async def run_test():
        from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool
        
        # Simulate the Azure OpenAI message format that was causing issues
        message_object = [{
            'id': 'msg_test123',
            'type': 'message',
            'role': 'assistant',
            'content': [
                {'type': 'output_text', 'text': '# Analysis: Refugees from France\n\nThis is the story content that was not being extracted properly.'}
            ]
        }]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.qmd', delete=False) as f:
            temp_path = f.name
        
        try:
            result = await create_quarto_notebook_tool(
                story_content=message_object,
                output_path=temp_path,
                title="Test Notebook",
                include_code_cells=False
            )
            
            assert result['status'] == 'success', f"Expected success, got: {result.get('status')}"
            print("  ✅ Quarto creation with message object successful")
            
            # Check the generated file
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Verify story content is properly extracted and in the output
            assert 'Analysis: Refugees from France' in content, "Story title should be extracted and in output"
            assert 'was not being extracted properly' in content, "Story content should be extracted and in output"
            
            # Most importantly: verify it does NOT contain the raw dict/JSON
            assert "[{'id': 'msg_test123'" not in content, "Raw message object should not be in output"
            print("  ✅ Message object properly extracted, no raw JSON in output")
            
        finally:
            # Cleanup
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return True
    
    return asyncio.run(run_test())


def test_get_data_for_story_integration():
    """Test that get_data_for_story properly integrates all tools."""
    print("\n🧪 Test 5: get_data_for_story tool integration...")
    
    import asyncio
    
    async def run_test():
        # This test requires MCP server to be running
        # For now, just verify the function exists and has the right structure
        from backend.mcp.tools.get_data_for_story import get_data_for_story_tool
        
        # Check function signature
        import inspect
        sig = inspect.signature(get_data_for_story_tool)
        params = list(sig.parameters.keys())
        
        assert 'question' in params, "Function should have question parameter"
        assert 'coo' in params, "Function should have coo parameter"
        assert 'coa' in params, "Function should have coa parameter"
        print("  ✅ Function signature is correct")
        
        # Check that the function calls the analysis tools
        # We'll do this by checking the source code
        import backend.mcp.tools.get_data_for_story as gdf_module
        source = inspect.getsource(gdf_module.get_data_for_story_tool)
        
        # Check for tool imports/calls
        assert 'analyze_data_statistics_tool' in source, "Should call analyze_data_statistics_tool"
        assert 'apply_analysis_guardrails_tool' in source, "Should call apply_analysis_guardrails_tool"
        assert 'extract_visualization_structure_tool' in source, "Should call extract_visualization_structure_tool"
        assert 'generate_visualization_description_tool' in source, "Should call generate_visualization_description_tool"
        print("  ✅ All analysis tools are called in get_data_for_story")
        
        return True
    
    return asyncio.run(run_test())


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Quarto Generation Fixes")
    print("=" * 60)
    
    tests = [
        test_story_content_extraction,
        test_template_metadata_handling,
        test_quarto_creation,
        test_quarto_creation_with_message_object,
        test_get_data_for_story_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
