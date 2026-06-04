"""Patch cognition/engine.py: publish neurotwin:twin_update after process_user state read."""
with open(r'D:\neurotwin\services\cognition\app\engine.py', 'r', encoding='utf-8') as f:
    c = f.read()

old = '''        finally:
            set_trace_id(None)

    async def _fetch_persona_with_timeout'''

new = '''            # ── Digital Twin integration: push cognitive state update ────────
            try:
                state_dict = cognitive_state.to_dict()
                twin_payload = json.dumps({
                    "user_id":         user_id,
                    "cognitive_state": state_dict,
                    "trace_id":        trace_id,
                    "source":          "cognition",
                    "timestamp":       datetime.now(timezone.utc).isoformat(),
                })
                await self.redis.publish("neurotwin:twin_update", twin_payload)
                logger.debug("Twin update published",
                             extra={"user_id": user_id, "trace_id": trace_id})
            except Exception as tw_err:
                logger.warning("Twin update publish failed",
                               extra={"user_id": user_id, "error": str(tw_err)})
        finally:
            set_trace_id(None)

    async def _fetch_persona_with_timeout'''

if old not in c:
    print("PATTERN NOT FOUND"); import sys; sys.exit(1)

c = c.replace(old, new, 1)
with open(r'D:\neurotwin\services\cognition\app\engine.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("PATCHED OK — cognition/engine.py")
