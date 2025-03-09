"""
Users blueprint for user profile management.
"""
from flask import Blueprint

users_bp = Blueprint("users", __name__)

from app.users import routes 