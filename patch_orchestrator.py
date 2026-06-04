"""Patch orchestrator/main.py: wire digital_twin profile fetch into orchestrate_conversation."""
with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add fetch_digital_twin_profile helper after publish_redis function
old_anchor = '''async def orchestrate_conversation('''

new_helper = '''async def fetch_digital_twin_profile(user_id: str) -> dict:
    """Fetch rich digital twin profile from digital_twin service. Graceful fallback."""
    try:
        async with get_traced_client(timeout=3.0) as client:
            resp = await client.get(f"{DIGITAL_TWIN_URL}/profile/{user_id}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Digital twin profile fetch failed: {e}")
    return {}


async def orchestrate_conversation('''

if old_anchor not in c:
    print("ANCHOR NOT FOUND"); import sys; sys.exit(1)

c = c.replace(old_anchor, new_helper, 1)

# 2. Replace the parallel tasks section to also fetch twin profile
old_tasks = '''    # Parallel tasks
    tasks = [
        ("memory", "log_conversation", {
            "user_id": user_id, "session_id": session_id,
            "content": message, "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"intent": intent.type}
        }),
        ("emotion", "detect_text", {"text": message, "user_id": user_id, "session_id": session_id}),
        ("persona", "get_user_profile", {"user_id": user_id}),
    ]'''

new_tasks = '''    # Parallel tasks (agents + digital twin profile fetched concurrently)
    tasks = [
        ("memory", "log_conversation", {
            "user_id": user_id, "session_id": session_id,
            "content": message, "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"intent": intent.type}
        }),
        ("emotion", "detect_text", {"text": message, "user_id": user_id, "session_id": session_id}),
        ("persona", "get_user_profile", {"user_id": user_id}),
    ]
    # Fetch digital twin profile concurrently with agent tasks
    twin_profile_task = asyncio.create_task(fetch_digital_twin_profile(user_id))'''

if old_tasks not in c:
    print("TASKS ANCHOR NOT FOUND"); import sys; sys.exit(1)

c = c.replace(old_tasks, new_tasks, 1)

# 3. After results are gathered, resolve the twin profile task
old_after = '''    emotion_data = results.get("emotion.detect_text", {})
    memory_log = results.get("memory.log_conversation", {})
    persona_data = results.get("persona.get_user_profile", {})'''

new_after = '''    # Resolve digital twin profile (non-blocking, was running concurrently)
    try:
        twin_profile_data = await asyncio.wait_for(twin_profile_task, timeout=2.0)
    except Exception:
        twin_profile_data = {}

    emotion_data = results.get("emotion.detect_text", {})
    memory_log = results.get("memory.log_conversation", {})
    persona_data = results.get("persona.get_user_profile", {})'''

if old_after not in c:
    print("AFTER ANCHOR NOT FOUND"); import sys; sys.exit(1)

c = c.replace(old_after, new_after, 1)

# 4. Use twin profile to build a richer system_prompt for CHAT
old_prompt = '''    else:
        system_prompt = persona_data.get("system_prompt", build_default_system_prompt(twin_profile))
        llm_response = await call_llm(message, system_prompt, context)'''

new_prompt = '''    else:
        system_prompt = build_twin_system_prompt(twin_profile_data, persona_data)
        llm_response = await call_llm(message, system_prompt, context)'''

if old_prompt not in c:
    print("PROMPT ANCHOR NOT FOUND"); import sys; sys.exit(1)

c = c.replace(old_prompt, new_prompt, 1)

with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("PATCHED OK — orchestrator/main.py (twin_profile fetch + system_prompt)")
