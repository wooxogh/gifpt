"""Shared LLM model tier constants for the 3-stage IR pipeline.

IR_MODEL is the model tier used by pseudocode IR, animation IR, and codegen.
Default is "gpt-4o" because Experiment A (Week 3) established a controlled
condition where all three pipeline stages share the same tier so that prompt
deltas are not confounded with model-tier deltas. See
`docs/snapshots/experiment-a-prompt-tweak.md`.

Override with GIFPT_IR_MODEL to run experiment C (model-tier A/B).
"""
import os

IR_MODEL = os.getenv("GIFPT_IR_MODEL", "gpt-4o")
