"""applyjob: an agent harness for honest, high-volume job applications.

The code does the deterministic work (search APIs, triage, rendering, auditing, the ledger).
The AI agent does the judgement work (writing, reading pages, filling forms) by following playbooks/.
Every fact about the applicant comes from workspace/profile/profile.json. Nothing is invented.
"""
__version__ = "0.1.0"
