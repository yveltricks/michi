import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from . import db

def from_json(json_str):
    """Convert JSON string to Python object"""
    if json_str:
        return json.loads(json_str)
    return []

# Add this after your imports
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))  # Optional
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, default=1)
    streak = db.Column(db.Integer, default=0)
    exp = db.Column(db.Integer, default=0)
    profile_pic = db.Column(db.String(200))
    
    # Updated unit preferences
    preferred_weight_unit = db.Column(db.String(10), default='kg')
    preferred_distance_unit = db.Column(db.String(10), default='km')
    preferred_measurement_unit = db.Column(db.String(10), default='cm')
    
    privacy_setting = db.Column(db.String(20), default='public')
    
    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True)
    routines = db.relationship('Routine', backref='user', lazy=True)
    measurements = db.relationship('Measurement', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)
    statistics = db.relationship('Statistic', backref='user', lazy=True)
    saved_items = db.relationship('SavedItem', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    # New relationships for following system
    following = db.relationship(
        'User', secondary='followers',
        primaryjoin='User.id==followers.c.follower_id',
        secondaryjoin='User.id==followers.c.followed_id',
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def badge(self):
        if self.level >= 16:
            return "Expert"
        elif self.level >= 6:
            return "Intermediate"
        else:
            return "Beginner"
            
    @property
    def next_level_exp(self):
        return (self.level + 1) * 100
        
    def update_level(self):
        self.level = self.exp // 100
        if self.level == 0:
            self.level = 1

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.String(50))
    volume = db.Column(db.Integer)
    exercises = db.Column(db.Text)  # Store as JSON string
    exp_gained = db.Column(db.Integer)
    session_rating = db.Column(db.Integer)
    title = db.Column(db.String(100), nullable=False, default='Workout')
    description = db.Column(db.Text)
    photo = db.Column(db.String(200))

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    equipment = db.Column(db.String(100))
    muscles_worked = db.Column(db.String(200))
    exercise_type = db.Column(db.String(20))
    user_created = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    photo = db.Column(db.String(200))

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50))
    goal = db.Column(db.String(100))
    muscle_groups = db.Column(db.String(200))
    exercises = db.Column(db.Text)  # Store as JSON string
    rest_time = db.Column(db.Integer)

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50))
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal_name = db.Column(db.String(100), nullable=False)
    target_value = db.Column(db.Float)
    current_value = db.Column(db.Float, default=0)
    is_complete = db.Column(db.Boolean, default=False)

class Statistic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_start_date = db.Column(db.Date)
    exp_gained = db.Column(db.Integer)
    workouts_completed = db.Column(db.Integer)
    total_volume = db.Column(db.Integer)

class SavedItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(20))  # 'routine' or 'exercise'
    folder_name = db.Column(db.String(100))
    date_saved = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)

class BodyweightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('bodyweight_logs', lazy=True))

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    weight = db.Column(db.Float)
    reps = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer)  # To maintain set order
    prev_weight = db.Column(db.Float)  # New column for previous weight
    prev_reps = db.Column(db.Integer)  # New column for previous reps
    has_previous = db.Column(db.Boolean, default=False)  # Flag to indicate if previous values exist

    # Add relationships
    exercise = db.relationship('Exercise', backref='sets')
    session = db.relationship('Session', backref='sets')