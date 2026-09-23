"""AquaLens multi-agent layer.

A small Coordinator agent plans a workflow over four specialised
sub-agents:

- :mod:`app.services.agent.scout`        — picks the Sentinel-2 scene
- :mod:`app.services.agent.historian`    — gathers trends and grounded news
- :mod:`app.services.agent.analyst`      — writes the narrative with self-critique
- :mod:`app.services.agent.reporter`     — writes the citizen-facing summary

Each agent is a focused Gemini call (or tool loop) with its own
system instruction and structured-output schema. The deterministic
risk model in :mod:`app.services.risk_model` remains the source of
truth for the numeric band; the agents only choose inputs and write
prose, never override the score.

The execution is captured by :mod:`app.services.agent.trace` and
persisted as an :class:`~app.models.AgentTrace` row per session.
"""
