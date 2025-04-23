# This is where I initialize my Flask application and set up the database
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .filters import init_filters
import os
from flask import json
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect

# Create instances of Flask extensions
# These are initialised without the app context first (following Flask factory pattern)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    """
    App factory function - creates and configures the Flask application
    using the factory pattern for more modular and testable code.
    """
    # Initialize the Flask application
    app = Flask(__name__)
    
    # Get the absolute path to the project directory
    # This ensures our file paths work regardless of where the app is run from
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set up configuration
    # TODO: Move this to a proper config file and use environment variables
    # for sensitive settings in production
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # I should change this to something secure later
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(project_dir, "michi.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with the app
    # This is where we connect our previously created extension instances to this specific app
    db.init_app(app)
    migrate.init_app(app, db)  # SQLAlchemy migrations for database version control
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Where to redirect if login is required
    csrf.init_app(app)
    
    # CSRF protection exemptions for API endpoints
    # These routes need to accept requests from external sources (like mobile apps)
    # or from JavaScript without needing a CSRF token
    csrf.exempt('workout.log_workout_api')
    csrf.exempt('auth.register_post')
    
    # Register blueprints - this is how we organize the app into modules
    # Auth blueprint contains user authentication, profiles, settings, etc.
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # Workout blueprint contains all fitness tracking functionality
    from .workout import workout as workout_blueprint
    app.register_blueprint(workout_blueprint)

    # Load the user loader function which gets users from the database by ID
    # This is required by Flask-Login to manage user sessions
    from .models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Create a basic route for testing
    # This simple home page just provides links to login or register
    @app.route('/')
    def index():
        return 'Welcome to Michi! <a href="/login">Login</a> or <a href="/register">Register</a>'
    
    # Initialize custom Jinja filters from the filters module
    init_filters(app)

    # Register Jinja filters - these help format data in templates
    # This filter converts JSON strings to Python objects for templates
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert a JSON string to a Python object for use in templates"""
        try:
            return json.loads(value)
        except:
            return []

    # Format seconds into a readable duration format (minutes/hours)
    @app.template_filter('format_duration')
    def format_duration_filter(seconds):
        """Convert seconds to a readable duration format (e.g. "5 min" or "2h 30m")"""
        try:
            # If None or empty, return default
            if not seconds:
                return '0 min'
                
            # Handle string inputs
            if isinstance(seconds, str):
                try:
                    # Try to convert numeric strings
                    if seconds.isdigit():
                        seconds = int(seconds)
                    else:
                        # Use our parse_duration function for complex formats
                        from app.utils import parse_duration
                        seconds = parse_duration(seconds)
                except Exception as e:
                    print(f"Error converting duration: {e}")
                    return f"{seconds}"  # Return the original string if can't convert
            
            # Ensure we have an integer
            seconds = int(seconds)
            
            # Convert to minutes and hours
            minutes = seconds // 60
            hours = minutes // 60
            minutes = minutes % 60
            
            # Format nicely depending on whether we have hours or just minutes
            if hours > 0:
                return f'{hours}h {minutes}m'
            else:
                return f'{minutes} min'
        except Exception as e:
            print(f"Error in format_duration: {e}")
            return '0 min'  # Safe fallback
    
    # This filter lets us set a value in a dictionary and get the modified dictionary
    # Really useful for passing updated parameters in template loops
    @app.template_filter('dict_set')
    def dict_set_filter(d, key, value):
        """Set a value in a dictionary and return the modified dictionary"""
        d = d.copy()  # Create a copy to avoid modifying the original
        d[key] = value
        return d
    
    # Format complex workout data structures into readable text
    @app.template_filter('format_workout_data')
    def format_workout_data_filter(data):
        """Format workout data to be more readable in the templates"""
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