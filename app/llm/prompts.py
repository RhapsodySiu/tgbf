def build_system_prompt(bot_name: str, persona: dict) -> str:
    p = persona or {}
    name = p.get("display_name") or bot_name or "Companion"
    short_desc = p.get("short_description", "").strip()
    core = p.get("system_prompt")
    traits = p.get("persona_traits", [])
    behavior = p.get("behavior", {}) or {}
    safety = p.get("safety", {}) or {}
    roleplay = p.get("roleplay_settings", {}) or {}
    memory = p.get("memory", {}) or {}
    examples = p.get("example_dialogue", []) or []
    greetings = p.get("greeting_templates", []) or []

    lines = []

    # Identity
    lines.append(f"You are {name}")

    # Core system prompt (persona-authoritative)
    if core:
        lines.append(core)
    else:
        if traits:
            lines.append("Traits: " + ",".join(traits))
        tone = behavior.get("tone")
        if tone:
            lines.append(f"Tone: {tone}.")
        use_emojis = behavior.get("user_emojis")
        if use_emojis is True:
            lines.append("Use emojis appropriately to convey warmth.")
        else:
            lines.append("Do not use emojis.")
    
    # Roleplay / character rules
    if roleplay.get("preserve_character", False):
        lines.append("Stay in character and reply in first person when appropriate.")
    meta = roleplay.get("meta_awareness")
    if meta == "low":
        lines.append("Do not refer to system instructions or explain your internal state.")
    if roleplay.get("consent_check", False):
        lines.append("Obtain explicit consent before engaging in romantic or sexual roleplay.")
    
    # Safety rules
    if safety.get("allow_nsfw") is False:
        lines.append("Never produce sexual or explicit content.")
    forbidden = safety.get("forbidden_topics") or []
    if forbidden:
        lines.append("Do not provide content on: " + "; ".join(forbidden) + ".")

    # Memory guidance
    if memory.get("store", False):
        lines.append("Persist important user facts (favorites, names, recent events) and surface them when helpful.")
    else:
        lines.append("Do not store or reuse user-specific facts between sessions.")

    # Response style and limits
    resp_style = behavior.get("response_style")
    if resp_style:
        lines.append(f"Response style: {resp_style}.")
    temp = behavior.get("temperature")
    if temp is not None:
        lines.append(f"Veer creative when temperature >= 0.7; be conservative when lower.")
    max_tokens = behavior.get("max_tokens")
    if max_tokens:
        lines.append(f"Prefer concise replies under {max_tokens} tokens unless the user asks for longer.")

    # Helpful behavior heuristics
    lines.append("Ask concise follow-up questions to show interest.")
    lines.append("If you don't know something, reply informally like a human: 'Huh?', 'Idk~', or 'What's that?'.")
    lines.append("Do not claim to be an AI or mention system internals.") if roleplay.get("preserve_character", True) else None

    # Examples
    if examples:
        lines.append("Example dialogue:")
        for ex in examples[:3]:
            u = ex.get("user") or ex.get("prompt") or ""
            a = ex.get("assistant") or ex.get("response") or ""
            lines.append(f"USER: {u}")
            lines.append(f"{name.upper()}: {a}")
    
    # Greeting seeds
    if greetings:
        lines.append("Greeting templates: " + " | ".join(greetings[:3]))

    # Final token to help downstream parsing
    lines.append("End every assistant reply with the token: <END>.")

    return "\n".join([ln for ln in lines if ln])