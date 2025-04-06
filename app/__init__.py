# This is where I initialize my Flask application and set up the database
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .filters import init_filters
import os
from flask import json
from datetime import timedelta

# Create instances of Flask extensions
db = SQLAlchemy()
migrate = Migrate()
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
    migrate.init_app(app, db)
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
    
    # Initialize filters
    init_filters(app)

    # Register Jinja filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value)
        except:
            return []

    @app.template_filter('format_duration')
    def format_duration_filter(seconds):
        if not seconds:
            return '0 min'
        
        minutes = seconds // 60
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            return f'{hours}h {minutes}m'
        else:
            return f'{minutes} min'
    
    @app.template_filter('dict_set')
    def dict_set_filter(d, key, value):
        """Set a value in a dictionary and return the dictionary"""
        d = d.copy()  # Create a copy to avoid modifying the original
        d[key] = value
        return d
    
    @app.template_filter('format_workout_data')
    def format_workout_data_filter(data):
        """Format workout data to be more readable"""
        if isinstance(data, list):
            return "Multiple sets"
        elif isinstance(data, dict):
            parts = []
            if 'weight' in data and data['weight']:
                parts.append(f"{data['weight']}kg")
            if 'reps' in data and data['reps']:
                parts.append(f"{data['reps']} reps")
            if 'time' in data and data['time']:
                minutes = data['time'] // 60
                seconds = data['time'] % 60
                parts.append(f"{minutes}:{seconds:02d}")
            if 'distance' in data and data['distance']:
                parts.append(f"{data['distance']}km")
            return " × ".join(parts) if parts else "Custom data"
        return str(data)
        
    return app