import pytest

@pytest.fixture
async def async_fixture():
    # Setup
    yield
    # Teardown

pytestmark = pytest.mark.asyncio