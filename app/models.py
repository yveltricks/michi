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
        """Calculate the experience needed for the next level"""
        # Simple linear progression: 100 * next level
        return (self.level + 1) * 100

    def update_level(self):
        """Update the user's level based on experience points"""
        try:
            # Calculate new level based on the current experience points
            # Simple formula: level = exp / 100 (rounded down to nearest integer)
            new_level = max(1, self.exp // 100)
            
            # Check if level has changed
            level_changed = new_level != self.level
            
            # Update the level if needed
            if level_changed:
                self.level = new_level
            
            # Return level info
            return {
                'leveled_up': level_changed,
                'new_level': self.level,
                'next_level_exp': (self.level + 1) * 100
            }
        except Exception as e:
            print(f"Error in update_level: {str(e)}")
            # Return safe values if there's an error
            return {
                'leveled_up': False,
                'new_level': self.level,
                'next_level_exp': (self.level + 1) * 100
            }

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
    sets_completed = db.Column(db.Integer, default=0)
    total_reps = db.Column(db.Integer, default=0)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    equipment = db.Column(db.String(100))
    muscles_worked = db.Column(db.String(200))
    exercise_type = db.Column(db.String(20))
    input_type = db.Column(db.String(20), default='weight_reps')  # weight_reps, bodyweight_reps, duration, distance_duration
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
            'units': {'weight': 'weight_unit', 'reps': 'reps'},
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
            'units': {'additional_weight': 'weight_unit', 'reps': 'reps'},
            'range_fields': ['min_reps', 'max_reps']
        },
        'assisted_bodyweight': {
            'fields': ['assistance_weight', 'reps'],
            'volume_formula': '(bodyweight - assistance_weight) * reps',
            'units': {'assistance_weight': 'weight_unit', 'reps': 'reps'},
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
            'volume_formula': 'weight * (time / 60) or bodyweight+weight * (time / 60) for planks',
            'units': {'weight': 'weight_unit', 'time': 'seconds'},
            'range_fields': ['min_duration', 'max_duration']
        },
        'distance_duration': {
            'fields': ['distance', 'time'],
            'volume_formula': None,
            'units': {'distance': 'distance_unit', 'time': 'seconds'},
            'range_fields': ['min_distance', 'max_distance', 'min_duration', 'max_duration']
        },
        'weight_distance': {
            'fields': ['weight', 'distance'],
            'volume_formula': 'weight * distance',
            'units': {'weight': 'weight_unit', 'distance': 'distance_unit'},
            'range_fields': ['min_distance', 'max_distance']
        }
    }

    def get_input_fields(self):
        """Return the required input fields for this exercise type"""
        return self.INPUT_TYPES.get(self.input_type, {}).get('fields', [])

    def get_units(self, user=None):
        """Return the units for each field, based on user preferences if available"""
        units = self.INPUT_TYPES.get(self.input_type, {}).get('units', {}).copy()
        
        # Replace dynamic unit placeholders with actual user preferences
        if user:
            for field, unit in units.items():
                if unit == 'weight_unit':
                    units[field] = user.preferred_weight_unit
                elif unit == 'distance_unit':
                    units[field] = user.preferred_distance_unit
        
        return units

    def get_range_fields(self):
        """Return the range fields for this exercise type"""
        return self.INPUT_TYPES.get(self.input_type, {}).get('range_fields', [])

    def calculate_volume(self, set_data, bodyweight=None, user=None):
        """Calculate volume based on exercise type and set data, respecting user's unit preferences"""
        input_type = self.INPUT_TYPES.get(self.input_type)
        if not input_type or not input_type['volume_formula']:
            return 0

        # Make a copy of set_data to avoid modifying the original
        data = set_data.copy() if set_data else {}
        
        # Convert weights and distances to kg/km for consistent volume calculation
        if user:
            # Import locally to avoid circular imports
            from .utils import normalize_weight_to_kg, normalize_distance_to_km
            
            weight_unit = user.preferred_weight_unit
            distance_unit = user.preferred_distance_unit
            
            # Normalize weight fields to kg
            if 'weight' in data and weight_unit:
                data['weight'] = normalize_weight_to_kg(data['weight'], weight_unit)
            if 'additional_weight' in data and weight_unit:
                data['additional_weight'] = normalize_weight_to_kg(data['additional_weight'], weight_unit)
            if 'assistance_weight' in data and weight_unit:
                data['assistance_weight'] = normalize_weight_to_kg(data['assistance_weight'], weight_unit)
                
            # Normalize distance to km
            if 'distance' in data and distance_unit:
                data['distance'] = normalize_distance_to_km(data['distance'], distance_unit)
                
            # If bodyweight is in lbs, convert it to kg
            if bodyweight and weight_unit == 'lbs':
                bodyweight = normalize_weight_to_kg(bodyweight, 'lbs')

        if self.input_type == 'bodyweight_reps':
            if not bodyweight:
                return 0
            return bodyweight * data.get('reps', 0)

        elif self.input_type == 'weighted_bodyweight':
            if not bodyweight:
                return 0
            return (bodyweight + data.get('additional_weight', 0)) * data.get('reps', 0)

        elif self.input_type == 'assisted_bodyweight':
            if not bodyweight:
                return 0
            return (bodyweight - data.get('assistance_weight', 0)) * data.get('reps', 0)

        elif self.input_type == 'weight_reps':
            return data.get('weight', 0) * data.get('reps', 0)

        elif self.input_type == 'weight_distance':
            return data.get('weight', 0) * data.get('distance', 0)

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

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'muscles_worked': self.muscles_worked,
            'input_type': self.input_type,
            'range_enabled': self.range_enabled,
            'range_min': self.min_reps,
            'range_max': self.max_reps
        }

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), default='Beginner')  # Beginner, Intermediate, Advanced
    goal = db.Column(db.String(20))  # Strength, Hypertrophy, etc.
    muscle_groups = db.Column(db.String(200))  # Comma-separated list of muscles
    exercises = db.Column(db.JSON)  # JSON data with exercises and their details
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = db.Column(db.Text)
    
    # Foreign key to the user who created the routine
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'goal': self.goal,
            'muscle_groups': self.muscle_groups.split(',') if self.muscle_groups else [],
            'exercises': self.exercises,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'description': self.description,
            'user_id': self.user_id
        }

# New Workout models for the routine feature
class Workout(db.Model):
    """Model for tracking a workout session"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, default=0)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=0)  # in seconds
    data = db.Column(db.Text, nullable=True)  # JSON string of workout data
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=True)
    exp_gained = db.Column(db.Integer, default=0)  # Store experience gained
    volume = db.Column(db.Float, default=0)  # Store total volume
    total_reps = db.Column(db.Integer, default=0)  # Total reps performed
    sets_completed = db.Column(db.Integer, default=0)  # Total sets completed
    completed = db.Column(db.Boolean, default=False)  # Whether workout is completed
    start_time = db.Column(db.DateTime, nullable=True)  # When workout was started
    end_time = db.Column(db.DateTime, nullable=True)  # When workout was completed
    
    # Relationships
    exercises = db.relationship('WorkoutExercise', backref='workout', cascade='all, delete-orphan', lazy=True)
    user = db.relationship('User', backref='workouts', lazy=True)
    
    def __repr__(self):
        return f'<Workout {self.title}>'

    def to_dict(self):
        """Convert workout to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'notes': self.notes,
            'description': self.notes,  # Alias for compatibility
            'rating': self.rating,
            'date': self.date.isoformat() if self.date else None,
            'duration': self.duration,
            'data': self.data,
            'routine_id': self.routine_id,
            'exercise_count': len(self.exercises),
            'exercises': [exercise.to_dict() for exercise in self.exercises],
            'exp_gained': self.exp_gained,
            'volume': self.volume,
            'total_reps': self.total_reps,
            'sets_completed': self.sets_completed,
            'completed': self.completed,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }
        
    @property
    def description(self):
        """Alias for notes field for compatibility"""
        return self.notes
        
    @description.setter
    def description(self, value):
        """Setter for notes via description alias"""
        self.notes = value

class WorkoutExercise(db.Model):
    """Model for an exercise in a workout"""
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    order = db.Column(db.Integer, default=1)  # Order in the workout
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    exercise = db.relationship('Exercise', lazy=True)
    sets = db.relationship('WorkoutSet', backref='workout_exercise', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        """Convert workout exercise to dictionary"""
        return {
            'id': self.id,
            'exercise_id': self.exercise_id,
            'exercise_name': self.exercise.name,
            'exercise_muscles': self.exercise.muscles_worked,
            'input_type': self.exercise.input_type,
            'order': self.order,
            'notes': self.notes,
            'sets': [workout_set.to_dict() for workout_set in self.sets]
        }

class WorkoutSet(db.Model):
    """Model for a set in a workout exercise"""
    id = db.Column(db.Integer, primary_key=True)
    workout_exercise_id = db.Column(db.Integer, db.ForeignKey('workout_exercise.id'), nullable=False)
    set_number = db.Column(db.Integer, default=1)
    
    # Common fields
    rest_duration = db.Column(db.Integer, nullable=True)  # in seconds
    completed = db.Column(db.Boolean, default=False)
    completion_time = db.Column(db.DateTime, nullable=True)
    
    # Specific input fields - only some will be used based on exercise input_type
    weight = db.Column(db.Float, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # in seconds
    distance = db.Column(db.Float, nullable=True)  # in meters
    additional_weight = db.Column(db.Float, nullable=True)  # for weighted bodyweight
    assistance_weight = db.Column(db.Float, nullable=True)  # for assisted bodyweight
    
    def to_dict(self):
        """Convert workout set to dictionary"""
        result = {
            'id': self.id,
            'set_number': self.set_number,
            'rest_duration': self.rest_duration,
            'completed': self.completed,
            'completion_time': self.completion_time.isoformat() if self.completion_time else None
        }
        
        # Add specific fields based on what's set
        if self.weight is not None:
            result['weight'] = self.weight
        if self.reps is not None:
            result['reps'] = self.reps
        if self.duration is not None:
            result['duration'] = self.duration
        if self.distance is not None:
            result['distance'] = self.distance
        if self.additional_weight is not None:
            result['additional_weight'] = self.additional_weight
        if self.assistance_weight is not None:
            result['assistance_weight'] = self.assistance_weight
            
        return result

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
    order = db.Column(db.Integer, default=0)
    set_type = db.Column(db.String(20), default='normal')  # normal, warmup, dropset, etc.
    volume = db.Column(db.Float, nullable=True)  # Store calculated volume for the set
    within_range = db.Column(db.Boolean, default=True)  # Whether the set was within the target range
    
    # Fields for different exercise types
    weight = db.Column(db.Float, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    time = db.Column(db.Integer, nullable=True)  # Duration in seconds
    distance = db.Column(db.Float, nullable=True)  # Distance in kilometers
    additional_weight = db.Column(db.Float, nullable=True)  # For weighted bodyweight exercises
    assistance_weight = db.Column(db.Float, nullable=True)  # For assisted bodyweight exercises

    # Relationships
    exercise = db.relationship('Exercise', backref='sets')
    session = db.relationship('Session', backref='sets')

    def to_dict(self, user=None):
        """Convert set data to dictionary based on exercise type"""
        exercise = self.exercise
        data = {
            'completed': self.completed,
            'set_type': self.set_type,
            'within_range': self.within_range
        }

        # Add relevant fields based on exercise type
        for field in exercise.get_input_fields():
            value = getattr(self, field)
            
            # Convert units based on user preferences
            if user and value is not None:
                # Import locally to avoid circular imports
                from .utils import convert_weight, convert_distance
                
                if field in ['weight', 'additional_weight', 'assistance_weight'] and user.preferred_weight_unit == 'lbs':
                    value = convert_weight(value, 'kg', 'lbs')
                elif field == 'distance' and user.preferred_distance_unit == 'mi':
                    value = convert_distance(value, 'km', 'mi')
            
            data[field] = value

        return data

    def check_within_range(self):
        """Check if the set was within the exercise's range"""
        if not self.exercise or not self.exercise.range_enabled:
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

class SharedRoutine(db.Model):
    """Model for public routine snapshots that appear in the explore page"""
    id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer, db.ForeignKey('routine.id'))
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), default='Beginner')
    goal = db.Column(db.String(20))
    muscle_groups = db.Column(db.String(200))
    exercises = db.Column(db.JSON)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to the user who created the routine
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Copy count - tracks how many times this routine has been copied
    copy_count = db.Column(db.Integer, default=0)
    
    # Define a relationship to the original routine
    original_routine = db.relationship('Routine', backref='shared_version')
    
    def to_dict(self):
        return {
            'id': self.id,
            'original_id': self.original_id,
            'name': self.name,
            'level': self.level,
            'goal': self.goal,
            'muscle_groups': self.muscle_groups.split(',') if self.muscle_groups else [],
            'exercises': self.exercises,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id,
            'copy_count': self.copy_count
        }