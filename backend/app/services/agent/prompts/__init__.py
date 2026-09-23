"""Structured-JSON system instructions for the multi-agent layer.

Each agent loads its own document via :func:`importlib.resources.files`.
JSON keeps the rules diff-friendly and unambiguous, and matches the
discipline we use for the deterministic narrator prompts in
:mod:`app.services.prompts`.
"""
