import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_run_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/run-task", json={"description": "Sample task"})
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["description"] == "Sample task"