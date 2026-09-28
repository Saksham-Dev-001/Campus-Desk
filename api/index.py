"""
Vercel serverless entry point for CampusDesk Flask app.
This file is the WSGI handler that Vercel's Python runtime calls.
"""
import sys
import os

# Add the project root to sys.path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects the WSGI app to be exported as 'app'
# This is it — Flask app is the WSGI callable
