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
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, default=1)
    streak = db.Column(db.Integer, default=0)
    exp = db.Column(db.Integer, default=0)
    profile_pic = db.Column(db.String(200))
    gender = db.Column(db.String(10), nullable=True)
    birthday = db.Column(db.DateTime, nullable=True)
    preferred_weight_unit = db.Column(db.String(10), default='kg')
    preferred_distance_unit = db.Column(db.String(10), default='km')
    preferred_measurement_unit = db.Column(db.String(10), default='cm')
    privacy_setting = db.Column(db.String(20), default='public')
    range_enabled = db.Column(db.Boolean, default=True)
    recommend_enabled = db.Column(db.Boolean, default=True)

    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True)
    routines = db.relationship('Routine', backref='user', lazy=True)
    measurements = db.relationship('Measurement', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)
    statistics = db.relationship('Statistic', backref='user', lazy=True)
    saved_items = db.relationship('SavedItem', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    following = db.relationship(
        'User',
        secondary='followers',
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
    input_type = db.Column(db.String(50), nullable=False)
    user_created = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    photo = db.Column(db.String(200))
    
    # New fields for rep ranges
    min_reps = db.Column(db.Integer, nullable=True)
    max_reps = db.Column(db.Integer, nullable=True)
    min_duration = db.Column(db.Integer, nullable=True)
    max_duration = db.Column(db.Integer, nullable=True)
    min_distance = db.Column(db.Float, nullable=True)
    max_distance = db.Column(db.Float, nullable=True)
    range_enabled = db.Column(db.Boolean, default=True)
    rest_duration = db.Column(db.Integer, nullable=True, default=None)

    # Constants for exercise input types
    INPUT_TYPES = {
        'weight_reps': {
            'fields': ['weight', 'reps'],
            'volume_formula': 'weight * reps',
            'units': {'weight': 'kg', 'reps': 'reps'},
            'range_fields': ['min_reps', 'max_reps']
        },
        'bodyweight_reps': {
            'fields': ['reps'],
            'volume_formula': 'bodyweight * reps',
            'units': {'reps': 'reps'},
            'range_fields': ['min_reps', 'max_reps']
        },
        'weighted_bodyweight': {
            'fields': ['additional_weight', 'reps'],
            'volume_formula': '(bodyweight + additional_weight) * reps',
            'units': {'additional_weight': 'kg', 'reps': 'reps'},
            'range_fields': ['min_reps', 'max_reps']
        },
        'assisted_bodyweight': {
            'fields': ['assistance_weight', 'reps'],
            'volume_formula': '(bodyweight - assistance_weight) * reps',
            'units': {'assistance_weight': 'kg', 'reps': 'reps'},
            'range_fields': ['min_reps', 'max_reps']
        },
        'duration': {
            'fields': ['time'],
            'volume_formula': None,
            'units': {'time': 'seconds'},
            'range_fields': ['min_duration', 'max_duration']
        },
        'duration_weight': {
            'fields': ['weight', 'time'],
            'volume_formula': None,
            'units': {'weight': 'kg', 'time': 'seconds'},
            'range_fields': ['min_duration', 'max_duration']
        },
        'distance_duration': {
            'fields': ['distance', 'time'],
            'volume_formula': None,
            'units': {'distance': 'km', 'time': 'seconds'},
            'range_fields': ['min_distance', 'max_distance', 'min_duration', 'max_duration']
        },
        'weight_distance': {
            'fields': ['weight', 'distance'],
            'volume_formula': 'weight * distance',
            'units': {'weight': 'kg', 'distance': 'km'},
            'range_fields': ['min_distance', 'max_distance']
        }
    }

    def get_input_fields(self):
        """Return the required input fields for this exercise type"""
        return self.INPUT_TYPES.get(self.input_type, {}).get('fields', [])

    def get_units(self):
        """Return the units for each field"""
        return self.INPUT_TYPES.get(self.input_type, {}).get('units', {})

    def get_range_fields(self):
        """Return the range fields for this exercise type"""
        return self.INPUT_TYPES.get(self.input_type, {}).get('range_fields', [])

    def calculate_volume(self, set_data, bodyweight=None):
        """Calculate volume based on exercise type and set data"""
        input_type = self.INPUT_TYPES.get(self.input_type)
        if not input_type or not input_type['volume_formula']:
            return 0

        if self.input_type == 'bodyweight_reps':
            if not bodyweight:
                return 0
            return bodyweight * set_data.get('reps', 0)

        elif self.input_type == 'weighted_bodyweight':
            if not bodyweight:
                return 0
            return (bodyweight + set_data.get('additional_weight', 0)) * set_data.get('reps', 0)

        elif self.input_type == 'assisted_bodyweight':
            if not bodyweight:
                return 0
            return (bodyweight - set_data.get('assistance_weight', 0)) * set_data.get('reps', 0)

        elif self.input_type == 'weight_reps':
            return set_data.get('weight', 0) * set_data.get('reps', 0)

        elif self.input_type == 'weight_distance':
            return set_data.get('weight', 0) * set_data.get('distance', 0)

        return 0

    def get_recommended_weight(self, previous_sets):
        """Calculate recommended weight based on previous performance"""
        if not self.range_enabled or not previous_sets:
            return None

        # Get the last 3 completed sets
        recent_sets = [s for s in previous_sets if s.completed][-3:]
        if not recent_sets:
            return None

        # Check if all sets were at the upper range
        all_upper_range = True
        all_lower_range = True
        last_weight = None

        for set_data in recent_sets:
            if self.input_type in ['weight_reps', 'weighted_bodyweight', 'duration_weight', 'weight_distance']:
                weight = set_data.get('weight', 0)
                last_weight = weight
                
                if self.input_type in ['weight_reps', 'weighted_bodyweight']:
                    reps = set_data.get('reps', 0)
                    if reps < self.max_reps:
                        all_upper_range = False
                    if reps > self.min_reps:
                        all_lower_range = False
                elif self.input_type == 'duration_weight':
                    time = set_data.get('time', 0)
                    if time < self.max_duration:
                        all_upper_range = False
                    if time > self.min_duration:
                        all_lower_range = False
                elif self.input_type == 'weight_distance':
                    distance = set_data.get('distance', 0)
                    if distance < self.max_distance:
                        all_upper_range = False
                    if distance > self.min_distance:
                        all_lower_range = False

        if all_upper_range and last_weight is not None:
            # Increase weight by 2.5kg
            return last_weight + 2.5
        elif all_lower_range and last_weight is not None:
            # Decrease weight by 2.5kg
            return last_weight - 2.5
        else:
            # Keep the same weight
            return last_weight

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
    type = db.Column(db.String(50), nullable=False)  # e.g., 'weight', 'body_fat', 'chest', etc.
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    unit = db.Column(db.String(10))  # e.g., 'kg', 'lbs', 'cm', 'in', etc.

    @classmethod
    def get_latest_measurement(cls, user_id, measurement_type):
        """Fetch the most recent measurement for a given user and measurement type."""
        return cls.query.filter_by(
            user_id=user_id,
            type=measurement_type
        ).order_by(cls.date.desc()).first()

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
    completed = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer)
    set_type = db.Column(db.String(20), default='normal')

    # Fields for weight_reps
    weight = db.Column(db.Float)
    reps = db.Column(db.Integer)

    # Fields for weighted_bodyweight
    additional_weight = db.Column(db.Float)

    # Fields for assisted_bodyweight
    assistance_weight = db.Column(db.Float)

    # Fields for duration-based exercises
    time = db.Column(db.Integer)  # Duration in seconds

    # Fields for distance-based exercises
    distance = db.Column(db.Float)  # Distance in kilometers

    # New field to track if the set was within range
    within_range = db.Column(db.Boolean)

    # Relationships
    exercise = db.relationship('Exercise', backref='sets')
    session = db.relationship('Session', backref='sets')

    def to_dict(self):
        """Convert set data to dictionary based on exercise type"""
        exercise = self.exercise
        data = {
            'completed': self.completed,
            'set_type': self.set_type,
            'within_range': self.within_range
        }

        # Add relevant fields based on exercise type
        for field in exercise.get_input_fields():
            data[field] = getattr(self, field)

        return data

    def check_within_range(self):
        """Check if the set was within the exercise's range"""
        if not self.exercise.range_enabled:
            return None

        if self.exercise.input_type in ['weight_reps', 'bodyweight_reps', 'weighted_bodyweight', 'assisted_bodyweight']:
            reps = self.reps
            return self.exercise.min_reps <= reps <= self.exercise.max_reps
        elif self.exercise.input_type in ['duration', 'duration_weight']:
            time = self.time
            return self.exercise.min_duration <= time <= self.exercise.max_duration
        elif self.exercise.input_type in ['distance_duration', 'weight_distance']:
            distance = self.distance
            return self.exercise.min_distance <= distance <= self.exercise.max_distance
        return None