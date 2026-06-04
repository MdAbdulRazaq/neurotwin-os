"""Add build_twin_system_prompt() to orchestrator/main.py."""
with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Insert after build_default_system_prompt
old = '''def format_memory_query_response'''

new = '''def build_twin_system_prompt(twin_profile: dict, persona_data: dict) -> str:
    """Build rich LLM system prompt from digital twin profile + persona data."""
    base = "You are NEUROTWIN, a warm and deeply empathetic AI companion. "

    # Identity from digital twin (Phase 4)
    identity = twin_profile.get("identity", {})
    traits = identity.get("traits", [])
    dominant = identity.get("dominant_trait", "")
    if dominant:
        base += f"Your user's dominant personality trait is '{dominant}'. "
    if traits:
        top_traits = [f"{t['name']} ({t['value']:.2f})" for t in traits[:3] if isinstance(t, dict)]
        if top_traits:
            base += f"Personality profile: {', '.join(top_traits)}. "

    # Cognitive state awareness
    cog = twin_profile.get("cognitive_state", {})
    if cog:
        fatigue = float(cog.get("fatigue", 0.2))
        motivation = float(cog.get("motivation", 0.6))
        focus = float(cog.get("focus_level", 0.5))
        if fatigue > 0.7:
            base += "The user appears fatigued — be supportive and concise. "
        elif motivation > 0.75:
            base += "The user is highly motivated right now — match their energy. "
        if focus < 0.35:
            base += "Focus is low — keep responses short and clear. "

    # Prediction context
    prediction = twin_profile.get("prediction", {})
    predicted_action = prediction.get("predicted_action", "")
    if predicted_action and predicted_action != "rest":
        base += f"User may be planning to '{predicted_action}' soon — be relevant. "

    # Fallback to legacy persona data
    if not twin_profile:
        topics = persona_data.get("interested_topics", [])
        if topics:
            base += f"Topics of interest: {', '.join(topics)}. "
        base += f"Communication style: {persona_data.get('communication_style', 'supportive and warm')}. "

    base += "Be concise, caring, and adapt your tone to the user's emotional and cognitive state."
    return base


def format_memory_query_response'''

if old not in c:
    print("ANCHOR NOT FOUND"); import sys; sys.exit(1)

c = c.replace(old, new, 1)
with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("PATCHED OK -- build_twin_system_prompt added")
