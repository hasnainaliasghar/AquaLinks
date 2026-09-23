"""Tool implementations callable by the agent layer.

Each module exports plain Python functions that:

1. Accept JSON-serialisable arguments only.
2. Return JSON-serialisable results (dict, list, or scalar).
3. Are deterministic given their inputs, or wrap an external service
   behind a thin adapter.

The Gemini function-declaration schemas live next to each agent in
``app/services/agent/<agent>.py`` so the same tool can advertise
different argument shapes to different agents when useful.
"""
