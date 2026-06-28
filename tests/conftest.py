"""
WhatsApp CRM SA — Pytest Configuration
======================================
Shared fixtures and test configuration.
"""

import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment before importing app modules
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-32-chars-minimum!!")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")