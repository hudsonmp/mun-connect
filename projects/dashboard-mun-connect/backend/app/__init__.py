"""
MUN Connect Flask Backend
-------------------------
Main application factory and configuration.
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_name="default"):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        config_name (str): Configuration environment to use
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration based on environment
    if config_name == "production":
        app.config.from_object("app.core.config.ProductionConfig")
    elif config_name == "testing":
        app.config.from_object("app.core.config.TestingConfig")
    else:
        app.config.from_object("app.core.config.DevelopmentConfig")
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register blueprints
    from app.auth import auth_bp
    from app.users import users_bp
    
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    
    # Register error handlers
    from app.core.errors import register_error_handlers
    register_error_handlers(app)
    
    # Initialize Supabase client (test connection)
    with app.app_context():
        try:
            from app.core.utils import create_supabase_client
            supabase = create_supabase_client()
            app.logger.info("Supabase connection established successfully")
        except Exception as e:
            app.logger.error(f"Failed to connect to Supabase: {str(e)}")
    
    # Shell context processor
    @app.shell_context_processor
    def make_shell_context():
        return {
            "db": db,
            "app": app,
        }
    
    return app 