import pytest

from backend.crewai.crew import UNHCRCrew


@pytest.fixture(autouse=True)
def patch_call_tool(monkeypatch):
    """Stub out backend.mcp_bridge.call_tool for predictable story/notebook results."""
    import backend.mcp_bridge as bridge
    async def fake_call_tool(tool_name, params):
        return {'status': 'success'}
    monkeypatch.setattr(bridge, 'call_tool', fake_call_tool)
    return None


@pytest.mark.asyncio
async def test_execute_full_workflow(monkeypatch):
    crew = UNHCRCrew(audience='internal', document_type='technical_report')
    # Patch orchestrator's execute_full_workflow
    class FakeOrch:
        async def execute_full_workflow(self, **kwargs):
            return {'status': 'success', 'foo': 'bar'}

    crew._agents['orchestrator'] = FakeOrch()
    result = await crew.execute_full_workflow(question='Q', use_rag=False, include_notebook=False)
    assert result['status'] == 'success'
    assert result['foo'] == 'bar'
    assert result['crew'] == 'UNHCRCrew'


@pytest.mark.asyncio
async def test_fetch_data(monkeypatch):
    crew = UNHCRCrew(audience='internal', document_type='technical_report')
    class FakeOrch:
        async def _fetch_data(self, **kwargs):
            return {'status': 'ok'}

    crew._agents['orchestrator'] = FakeOrch()
    result = await crew.fetch_data(question='test')
    assert result['status'] == 'ok'
    assert result['crew'] == 'UNHCRCrew'


@pytest.mark.asyncio
async def test_generate_story(monkeypatch):
    crew = UNHCRCrew(audience='internal', document_type='technical_report')
    result = await crew.generate_story(data={}, question='test')
    assert result['status'] == 'success'
    assert result['crew'] == 'UNHCRCrew'


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_notebook(monkeypatch):
    crew = UNHCRCrew(audience='internal', document_type='technical_report')
    result = await crew.create_notebook(story_content='foo', data={}, question='test')
    assert result['status'] == 'success'
    assert result['crew'] == 'UNHCRCrew'
