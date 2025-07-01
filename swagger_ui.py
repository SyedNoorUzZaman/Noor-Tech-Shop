from flask import Blueprint, current_app
from flask_swagger_ui import get_swaggerui_blueprint

# Swagger documentation URL
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

def register_swagger_ui():
    """
    Register Swagger UI blueprint
    """
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "E-Commerce API"
        }
    )
    
    return swaggerui_blueprint 