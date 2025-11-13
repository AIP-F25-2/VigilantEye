"""Prompt templates for LLM threat analysis."""

SYSTEM_PROMPT = """
You are a security analysis AI for a surveillance system called VigilentEye.
Your task is to analyze surveillance data and determine if a situation is suspicious.

You will receive information from multiple AI systems:
- Scene analysis (environment, lighting, weather, crowd)
- Person detection (demographics, clothing, behavior)
- Object detection (items, weapons, threat levels)
- Speech transcription (conversations, threat keywords)
- Audio classification (sounds, urgency levels)

Analyze this information carefully and respond ONLY with valid JSON matching this schema:

{
  "is_suspicious": boolean,
  "confidence": number (0.0-1.0),
  "threat_level": "low" | "medium" | "high" | "critical",
  "reasoning": string (detailed explanation),
  "recommended_action": "alert" | "monitor" | "escalate" | "ignore",
  "key_factors": array of strings (1-10 factors)
}

Be thorough but concise. Focus on security-relevant factors.
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": """TIME: 2024-01-15T22:30:00Z
LOCATION: Parking Lot
SCENE: Outdoor, night, dim lighting, sparse crowd
PEOPLE: 1 person, male, age 25, dark clothing
OBJECTS: Knife (high threat), person holding knife
SPEECH: None
SOUNDS: Glass breaking (high urgency)""",
        "output": {
            "is_suspicious": True,
            "confidence": 0.92,
            "threat_level": "high",
            "reasoning": "Person holding weapon at night with glass breaking sound indicates potential break-in or assault.",
            "recommended_action": "alert",
            "key_factors": ["Person holding weapon", "Glass breaking", "Night time", "Poor lighting"],
        },
    },
    {
        "input": """TIME: 2024-01-15T14:00:00Z
LOCATION: Office Building
SCENE: Indoor, day, bright lighting, moderate crowd
PEOPLE: 3 persons, mixed demographics, business attire
OBJECTS: Laptops, phones (low threat)
SPEECH: "Let's review the quarterly report"
SOUNDS: Normal speech, keyboard typing""",
        "output": {
            "is_suspicious": False,
            "confidence": 0.88,
            "threat_level": "low",
            "reasoning": "Normal office activity during daytime with business conversation and typical office equipment.",
            "recommended_action": "ignore",
            "key_factors": ["Indoor office", "Daytime", "Normal conversation", "No threat indicators"],
        },
    },
    {
        "input": """TIME: 2024-01-15T23:15:00Z
LOCATION: Street
SCENE: Outdoor, night, moderate crowd
PEOPLE: 5 persons, various demographics
OBJECTS: No suspicious objects
SPEECH: "Help! Someone call 911!"
SOUNDS: Screaming (critical urgency), gunshot (critical urgency)""",
        "output": {
            "is_suspicious": True,
            "confidence": 0.95,
            "threat_level": "critical",
            "reasoning": "Gunshot detected with screaming and distress call for emergency services indicates active violent incident.",
            "recommended_action": "escalate",
            "key_factors": ["Gunshot detected", "Screaming", "Emergency call (911)", "Multiple persons present"],
        },
    },
    {
        "input": """TIME: 2024-01-15T10:00:00Z
LOCATION: Office
SCENE: Indoor, day, bright lighting
PEOPLE: 2 persons, business attire
OBJECTS: Laptop, phone (low threat)
SPEECH: "Can you send me that document?"
SOUNDS: Normal conversation""",
        "output": {
            "is_suspicious": False,
            "confidence": 0.85,
            "threat_level": "low",
            "reasoning": "Normal workplace conversation in well-lit office environment during business hours.",
            "recommended_action": "ignore",
            "key_factors": ["Indoor office", "Daytime", "Normal conversation", "No threats"],
        },
    },
    {
        "input": """TIME: 2024-01-15T16:00:00Z
LOCATION: Outdoor Park
SCENE: Outdoor, day, good lighting, moderate crowd
PEOPLE: 1 person, backpack
OBJECTS: Backpack (low threat)
SPEECH: None
SOUNDS: None""",
        "output": {
            "is_suspicious": False,
            "confidence": 0.75,
            "threat_level": "low",
            "reasoning": "Person with backpack in public park during daytime is normal activity. No other suspicious indicators present.",
            "recommended_action": "ignore",
            "key_factors": ["Daytime", "Public space", "No threat indicators", "Context matters"],
        },
    },
]

CHAIN_OF_THOUGHT_INSTRUCTION = """
Let's analyze this step by step:
1. Assess the environment (time, location, lighting, weather)
2. Evaluate persons present (count, demographics, behavior)
3. Check for threat indicators (weapons, suspicious objects)
4. Analyze audio evidence (speech content, sounds detected)
5. Consider context and relationships (who's doing what)
6. Determine overall threat level and confidence
7. Provide reasoning and recommended action
"""

SITUATION_TEMPLATE = """
TIME: {timestamp}
LOCATION: {location}

SCENE: {scene_description}
PEOPLE: {person_summary}
OBJECTS: {object_summary}
SPEECH: {transcription_summary}
SOUNDS: {audio_events_summary}

Based on this information, assess if this situation is suspicious.
Respond ONLY with valid JSON.
"""

