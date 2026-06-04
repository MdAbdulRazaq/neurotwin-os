"""
Agent Runner — Starts all 4 autonomous agents concurrently.
"""

import asyncio
import logging

from memory_agent import main as memory_main
from emotion_agent import main as emotion_main
from persona_agent import main as persona_main
from insight_agent import main as insight_main

logger = logging.getLogger("agents.runner")

async def main():
    logger.info("Starting all agents...")
    await asyncio.gather(
        memory_main(),
        emotion_main(),
        persona_main(),
        insight_main(),
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    asyncio.run(main())
