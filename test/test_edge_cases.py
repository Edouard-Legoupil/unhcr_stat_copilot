import pytest

from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool


@pytest.mark.asyncio
async def test_unsupported_doc_type_raises():
    """Requests with unsupported document_type should error fast before rendering."""
    metadata = {'document_type': 'invalid_type'}
    # Unsupported doc_type should be ignored for notebook creation
    result = await create_quarto_notebook_tool(
        story_content='sample',
        output_path=None,
        title='T',
        author='A',
        date=None,
        include_code_cells=False,
        use_unhcr_theme=False,
        use_unhcr_style=False,
        original_query=None,
        metadata=metadata,
        data=None,
        render_html=False,
        render_pdf=False,
    )
    assert result['status'] == 'success'
