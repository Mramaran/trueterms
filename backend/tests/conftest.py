"""Pytest setup: make backend modules importable the same way api_server.py does
(api_server.py inserts the backend folder into sys.path and imports modules flat)."""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
