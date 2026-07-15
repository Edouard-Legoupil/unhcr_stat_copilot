#!/usr/bin/env python3
"""
Test script to verify the integration of analyze_data_statistics 
and apply_analysis_guardrails into the get_data_for_story workflow.
"""

import asyncio
from backend.mcp.tools.get_data_for_story import get_data_for_story_tool
from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
from backend.mcp.common import UNHCRAPIClient


import pytest

@pytest.mark.asyncio
async def test_integration():
    """Test that the enhanced pipeline works correctly."""
    
    print("=" * 70)
    print("Testing Tool Integration: Phase 1")
    print("=" * 70)
    
    # Initialize API client
    api_client = UNHCRAPIClient()
    
    # Test question
    question = "Refugees from France in the last 10 years"
    
    print(f"\n📝 Testing with question: {question}")
    
    # Step 1: Get data for story (should now include statistics and guardrails)
    print("\n1️⃣  Calling get_data_for_story_tool...")
    try:
        data_result = await get_data_for_story_tool(
            api_client=api_client,
            question=question,
            coo="FRA",
            years="2015-2024"
        )
        
        print(f"   ✅ Data retrieved successfully")
        print(f"   📊 Data type: {data_result.get('data_type')}")
        print(f"   📦 Number of items: {len(data_result.get('data', {}).get('items', []))}")
        
        # Check if statistics were added
        if 'statistics' in data_result.get('data', {}):
            print(f"   ✅ Statistics added to data!")
            stats = data_result['data']['statistics']
            print(f"      - Statistics keys: {list(stats.keys())}")
            if 'statistics' in stats:
                print(f"      - Number of fields analyzed: {len(stats['statistics'])}")
                for field, stat_data in list(stats['statistics'].items())[:3]:
                    print(f"        • {field}: mean={stat_data.get('mean', 'N/A'):.2f}, "
                          f"median={stat_data.get('median', 'N/A'):.2f}")
        else:
            print(f"   ⚠️  Statistics NOT added (might be API issue or no numeric data)")
        
        # Check if guardrails were added
        if 'guardrails' in data_result.get('data', {}):
            print(f"   ✅ Guardrails added to data!")
            guardrails = data_result['data']['guardrails']
            print(f"      - Overall compliant: {guardrails.get('overall_compliant', 'N/A')}")
            print(f"      - Compliance percentage: {guardrails.get('compliance_percentage', 0):.0f}%")
            print(f"      - Compliance level: {guardrails.get('compliance_level', 'N/A')}")
        else:
            print(f"   ⚠️  Guardrails NOT added (might be API issue)")
            
    except Exception as e:
        print(f"   ❌ Error in get_data_for_story: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Generate story with enriched data
    print("\n2️⃣  Calling generate_analytical_story_tool with enriched data...")
    try:
        story_result = await generate_analytical_story_tool(
            data=data_result,
            question=question,
            audience="internal",
            document_type="long_read"
        )
        
        print(f"   ✅ Story generated successfully")
        
        # Extract story content
        story = story_result.get('story', '')
        if isinstance(story, list):
            story = '\n'.join(story)
        
        print(f"   📄 Story length: {len(story)} characters")
        print(f"   🎯 Title: {story_result.get('title', 'N/A')}")
        
        # Check if statistics appear in story
        if 'Statistical Analysis' in story or 'mean=' in story:
            print(f"   ✅ Statistics included in story!")
        else:
            print(f"   ⚠️  Statistics might not be in story")
        
        # Check if compliance appears in story
        if 'UNHCR Compliance' in story or 'Compliance' in story:
            print(f"   ✅ Compliance information included in story!")
        else:
            print(f"   ⚠️  Compliance might not be in story")
            
    except Exception as e:
        print(f"   ❌ Error in generate_analytical_story: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Show sample output
    print("\n3️⃣  Sample Story Output:")
    print("   " + "-" * 66)
    story = story_result.get('story', '')
    if isinstance(story, list):
        story = '\n'.join(story)
    lines = story.split('\n')
    
    # Show first 20 lines
    for i, line in enumerate(lines[:20]):
        print(f"   {line}")
    
    if len(lines) > 20:
        print(f"   ... ({len(lines) - 20} more lines)")
    
    print("   " + "-" * 66)
    
    print("\n" + "=" * 70)
    print("✅ Integration Test Complete!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    exit(0 if success else 1)
