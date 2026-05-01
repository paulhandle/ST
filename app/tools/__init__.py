"""Platform-owned external integrations (COROS, Garmin, Strava, manual upload).

Tools provide read/write access to third-party data sources. Skills do not
import tools directly — they receive only the summarized data the orchestrator
chooses to pass via SkillContext.
"""
