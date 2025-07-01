from flask import Blueprint, current_app
from flask_swagger_ui import get_swaggerui_blueprint

# Swagger documentation URL for admin API
SWAGGER_URL = '/admin/api/docs'
API_URL = '/static/swagger/swagger.json'

def register_admin_swagger_ui():
    """
    Register Admin Swagger UI blueprint
    """
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Admin API"
        }
    )
    
    return swaggerui_blueprint 