"""
Vercel Python entry point - imports the main app
"""
from api.index import app

# Export the app for Vercel
handler = app