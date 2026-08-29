"""The reserved client_id the deployed dashboard falls back to.

Anyone opening the dashboard link without the extension installed has no
client_id of their own, so instead of an empty page they get this seeded
history (see backend/scripts/seed_demo.py). /scan refuses to write under
this id, so the showcase can't be polluted by real traffic.
"""

DEMO_CLIENT_ID = "demo"
