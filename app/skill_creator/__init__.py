"""Skill creator: distills past training programs into reusable Skills.

The goal is to take a body of historical coach-prescribed workouts and
extract the methodology — volume curve, intensity distribution, workout
patterns, periodization rhythm — into a Skill spec that can generate
similar plans for future training cycles.

Pipeline:
  raw COROS schedule  →  scripts/extract_past_plans.py
                       ↓
             var/extracted_plans/<label>.json
                       ↓
                 analyze (this module)
                       ↓
             methodology summary + spec
                       ↓
            user review + edits (chat)
                       ↓
        app/skills/user_extracted/<slug>/
"""
