import os
import tempfile
import pytest

from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool


@pytest.fixture(autouse=True)
def deterministic_env(monkeypatch):
    monkeypatch.setenv('QUARTO_DETERMINISTIC', 'true')
    monkeypatch.setenv('TEMPLATE_VERSION', 'v0.0-test')
    monkeypatch.setenv('LLM_MODEL', 'test-model')
    return True


@pytest.mark.asyncio
async def test_quarto_notebook_golden(tmp_path):
    """Golden-file test: fixed input produces expected .qmd skeleton."""
    story = "This is a test story."
    data = {'items': [{'year': 2020, 'value': 100}]}
    metadata = {'document_type': 'technical_report', 'audience': 'internal', 'analysis_config': {'model': 'test-model'}}
    output = await create_quarto_notebook_tool(
        story_content=story,
        output_path=None,
        title='Test Title',
        author='Tester',
        date=None,
        include_code_cells=True,
        use_unhcr_theme=False,
        use_unhcr_style=False,
        original_query='unit test',
        metadata=metadata,
        data=data,
        render_html=False,
        render_pdf=False,
    )
    content = output['content']
    # Check front matter markers and deterministic timestamp
    assert content.startswith('---')
    assert 'template_version: v0.0-test' in content
    assert 'model_version: test-model' in content
    assert '1970-01-01T00:00:00Z' in content
    # Check code fence for data visualization
    assert '```{python}' in content
    # Ensure story content present
    assert 'This is a test story.' in content
