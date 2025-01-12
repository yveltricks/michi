# This is where I initialize my Flask application and set up the database
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from .filters import init_filters
import os

# Create instances of Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    # Initialize the Flask application
    app = Flask(__name__)
    
    # Get the absolute path to the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set up configuration
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # I should change this to something secure later
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(project_dir, "michi.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # Add this after registering the auth blueprint
    from .workout import workout as workout_blueprint
    app.register_blueprint(workout_blueprint)

    # Load the user loader function
    from .models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Create a basic route for testing
    @app.route('/')
    def index():
        return 'Welcome to Michi! <a href="/login">Login</a> or <a href="/register">Register</a>'
    
    init_filters(app)
    return app