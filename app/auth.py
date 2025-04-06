from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Session, Measurement, Workout, Exercise, WorkoutLike, WorkoutComment, Notification
from sqlalchemy import desc
from . import db
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
import json
from .workout import calculate_workout_metrics  # Import the function from workout.py
from .utils import convert_volume_to_preferred_unit, calculate_weekly_stats, compare_exercise_progress

@dataclass
class YearRange:
    start: int
    end: int

auth = Blueprint('auth', __name__)

# Add this after USERNAME_PATTERN:
PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,200}$')
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,20}$')

def validate_weight(weight_value, unit='kg'):
    """
    Validate weight input
    Returns tuple of (is_valid, message)
    """
    try:
        weight = float(weight_value)

        # Convert lbs to kg if needed
        if unit == 'lbs':
            weight = weight * 0.45359237
            min_weight = 11  # 5kg in lbs
            max_weight = 1322  # 600kg in lbs
        else:
            min_weight = 5
            max_weight = 600

        if weight < min_weight:
            return False, f"Weight must be at least {min_weight} {unit}"
        if weight > max_weight:
            return False, f"Weight cannot exceed {max_weight} {unit}"

        return True, None

    except (ValueError, TypeError):
        return False, "Please enter a valid weight"

@auth.route('/home')
@login_required
def home():
    """Display the home feed with recent workouts and achievements"""
    # Get user's recent workouts
    recent_workouts = Workout.query.filter_by(user_id=current_user.id)\
        .filter(Workout.completed == True)\
        .order_by(Workout.date.desc())\
        .limit(5)\
        .all()
    
    # Get workouts from followed users
    followed_workouts = Workout.query.join(User)\
        .filter(User.id.in_([u.id for u in current_user.following]))\
        .filter(Workout.completed == True)\
        .order_by(Workout.date.desc())\
        .limit(5)\
        .all()
    
    # Calculate weekly stats for the current user
    weekly_stats = calculate_weekly_stats(current_user.id)
    
    # Make sure the weekly stats have default values if they're empty
    if not weekly_stats.get('current_week'):
        weekly_stats['current_week'] = {
            'workout_count': 0,
            'total_volume': 0,
            'total_duration': 0,
            'total_exp': 0
        }
    
    if not weekly_stats.get('comparisons'):
        weekly_stats['comparisons'] = {
            'workout_count': 0,
            'total_volume': 0,
            'total_duration': 0,
            'total_exp': 0
        }
    
    # Process each workout to get additional data
    combined_sessions = []
    
    # Process recent workouts
    for workout in recent_workouts:
        try:
            # Compare exercise performance with previous workouts
            exercise_comparisons = compare_exercise_progress(workout.id, current_user.id)
            
            # Load workout data
            data = json.loads(workout.data) if workout.data else {}
            exercises = data.get('exercises', [])
            
            # Use our metrics calculation function to get accurate metrics
            metrics = calculate_workout_metrics(data)
            
            # Use stored values if they exist, otherwise use calculated values
            volume = workout.volume if hasattr(workout, 'volume') and workout.volume else metrics['volume']
            
            # Convert volume from kg to user's preferred unit
            volume = convert_volume_to_preferred_unit(volume, current_user.preferred_weight_unit)
            
            duration = workout.duration if hasattr(workout, 'duration') and workout.duration else metrics['duration']
            rating = workout.rating if hasattr(workout, 'rating') and workout.rating else metrics['rating']
            
            # Process each exercise to ensure it has an ID
            for exercise in exercises:
                if isinstance(exercise, dict):
                    # If the exercise is a dictionary without an ID, try to find the exercise
                    if 'id' not in exercise:
                        exercise_name = exercise.get('name')
                        if exercise_name:
                            db_exercise = Exercise.query.filter_by(name=exercise_name).first()
                            if db_exercise:
                                exercise['id'] = db_exercise.id
                    # If still no ID, generate a temporary one
                    if 'id' not in exercise:
                        exercise['id'] = f"temp_{hash(exercise.get('name', ''))}"
                    
                    # Add comparison indicator if available
                    if 'id' in exercise and exercise['id'] in exercise_comparisons:
                        exercise['comparison'] = exercise_comparisons[exercise['id']]
            
            # Check for exercise sets format and calculate sets count if needed
            for exercise in exercises:
                if isinstance(exercise, dict) and 'sets' in exercise and isinstance(exercise['sets'], list):
                    # Count sets
                    exercise['sets_count'] = len(exercise['sets'])
                    
                    # If there's no volume in the exercise but there is in the sets, calculate total
                    if 'volume' not in exercise:
                        exercise_volume = 0
                        for set_data in exercise['sets']:
                            if isinstance(set_data, dict) and 'volume' in set_data:
                                exercise_volume += float(set_data['volume'])
                            elif isinstance(set_data, dict) and 'weight' in set_data and 'reps' in set_data:
                                exercise_volume += float(set_data['weight']) * float(set_data['reps'])
                        exercise['volume'] = exercise_volume
                    
                    # Convert exercise volume to preferred unit if it exists
                    if 'volume' in exercise:
                        exercise['volume'] = convert_volume_to_preferred_unit(exercise['volume'], current_user.preferred_weight_unit)
            
            # Get like count
            like_count = WorkoutLike.query.filter_by(workout_id=workout.id).count()
            
            # Check if current user has liked this workout
            user_liked = WorkoutLike.query.filter_by(
                workout_id=workout.id, 
                user_id=current_user.id
            ).first() is not None
            
            # Get comment count
            comment_count = WorkoutComment.query.filter_by(workout_id=workout.id).count()
            
            # Get user's level at the time of the workout
            user_level = calculate_user_level_at_time(current_user.id, workout.date)
            
            combined_sessions.append({
                'id': workout.id,
                'date': workout.date,
                'session_date': workout.date,  # Add session_date for template compatibility
                'title': workout.title,
                'exercises': exercises,
                'user': current_user,
                'is_own': True,
                'description': workout.notes if hasattr(workout, 'notes') and workout.notes else (
                    data.get('description', '') if isinstance(data, dict) else ''
                ),
                'duration': duration,
                'volume': volume,
                'session_rating': rating,
                'like_count': like_count,
                'user_liked': user_liked,
                'comment_count': comment_count,
                'user_level': user_level,
                'photo': workout.photo
            })
        except Exception as e:
            print(f"Error processing recent workout: {e}")
            continue
    
    # Process followed users' workouts
    for workout in followed_workouts:
        try:
            data = json.loads(workout.data) if workout.data else {}
            exercises = data.get('exercises', [])
            
            # Use our metrics calculation function to get accurate metrics
            metrics = calculate_workout_metrics(data)
            
            # Use stored values if they exist, otherwise use calculated values
            volume = workout.volume if hasattr(workout, 'volume') and workout.volume else metrics['volume']
            
            # Convert volume from kg to user's preferred unit
            volume = convert_volume_to_preferred_unit(volume, current_user.preferred_weight_unit)
            
            duration = workout.duration if hasattr(workout, 'duration') and workout.duration else metrics['duration']
            rating = workout.rating if hasattr(workout, 'rating') and workout.rating else metrics['rating']
            
            # Process each exercise to ensure it has an ID
            for exercise in exercises:
                if isinstance(exercise, dict):
                    # If the exercise is a dictionary without an ID, try to find the exercise
                    if 'id' not in exercise:
                        exercise_name = exercise.get('name')
                        if exercise_name:
                            db_exercise = Exercise.query.filter_by(name=exercise_name).first()
                            if db_exercise:
                                exercise['id'] = db_exercise.id
                    # If still no ID, generate a temporary one
                    if 'id' not in exercise:
                        exercise['id'] = f"temp_{hash(exercise.get('name', ''))}"
            
            # Check for exercise sets format and calculate sets count if needed
            for exercise in exercises:
                if isinstance(exercise, dict) and 'sets' in exercise and isinstance(exercise['sets'], list):
                    # Count sets
                    exercise['sets_count'] = len(exercise['sets'])
                    
                    # If there's no volume in the exercise but there is in the sets, calculate total
                    if 'volume' not in exercise:
                        exercise_volume = 0
                        for set_data in exercise['sets']:
                            if isinstance(set_data, dict) and 'volume' in set_data:
                                exercise_volume += float(set_data['volume'])
                            elif isinstance(set_data, dict) and 'weight' in set_data and 'reps' in set_data:
                                exercise_volume += float(set_data['weight']) * float(set_data['reps'])
                        exercise['volume'] = exercise_volume
                    
                    # Convert exercise volume to preferred unit if it exists
                    if 'volume' in exercise:
                        exercise['volume'] = convert_volume_to_preferred_unit(exercise['volume'], current_user.preferred_weight_unit)
            
            # Get like count
            like_count = WorkoutLike.query.filter_by(workout_id=workout.id).count()
            
            # Check if current user has liked this workout
            user_liked = WorkoutLike.query.filter_by(
                workout_id=workout.id, 
                user_id=current_user.id
            ).first() is not None
            
            # Get comment count
            comment_count = WorkoutComment.query.filter_by(workout_id=workout.id).count()
            
            # Get user's level at the time of the workout
            user_level = calculate_user_level_at_time(workout.user_id, workout.date)
            
            combined_sessions.append({
                'id': workout.id,
                'date': workout.date,
                'session_date': workout.date,  # Add session_date for template compatibility
                'title': workout.title,
                'exercises': exercises,
                'user': workout.user,
                'is_own': False,
                'description': workout.notes if hasattr(workout, 'notes') and workout.notes else (
                    data.get('description', '') if isinstance(data, dict) else ''
                ),
                'duration': duration,
                'volume': volume,
                'session_rating': rating,
                'like_count': like_count,
                'user_liked': user_liked,
                'comment_count': comment_count,
                'user_level': user_level,
                'photo': workout.photo
            })
        except Exception as e:
            print(f"Error processing followed workout: {e}")
            continue
    
    # Sort combined sessions by date
    combined_sessions.sort(key=lambda x: x['date'], reverse=True)
    
    # Get unread notification count
    unread_notification_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('home.html', 
                          sessions=combined_sessions, 
                          weekly_stats=weekly_stats,
                          unread_notification_count=unread_notification_count)

def calculate_user_level_at_time(user_id, date):
    """Calculate what level a user was at a given time"""
    from app.models import User, Workout
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        return 1  # Default level
    
    # Get current level
    current_level = user.level
    current_exp = user.exp
    
    # Get workouts completed after the given date
    later_workouts = Workout.query.filter(
        Workout.user_id == user_id,
        Workout.date > date,
        Workout.completed == True
    ).all()
    
    # Calculate EXP gained after the given date
    exp_after_date = sum(w.exp_gained or 0 for w in later_workouts)
    
    # Estimate EXP at the given date
    est_exp_at_date = max(0, current_exp - exp_after_date)
    
    # Calculate level at that EXP
    level_at_date = max(1, est_exp_at_date // 100)
    
    return level_at_date

@auth.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('auth.home'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register')
def register():
    current_year = datetime.utcnow().year
    # Calculate year range for the dropdown
    # Start from current_year - 150 (oldest possible age)
    # End at current_year - 5 (minimum age requirement)
    year_range = YearRange(
        start=current_year - 150,
        end=current_year - 5
    )
    return render_template('register.html', year_range=year_range)

@auth.route('/register', methods=['POST'])
def register_post():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    gender = request.form.get('gender')

    # Get bodyweight data
    bodyweight = request.form.get('bodyweight')
    weight_unit = request.form.get('weight_unit', 'kg')

    # Validate weight
    is_valid, message = validate_weight(bodyweight, weight_unit)
    if not is_valid:
        flash(message)
        return redirect(url_for('auth.register'))

    # Convert to kg if in lbs
    weight_value = float(bodyweight)
    if weight_unit == 'lbs':
        weight_value = weight_value * 0.45359237

    # Get birthday components
    birth_day = request.form.get('birth_day')
    birth_month = request.form.get('birth_month')
    birth_year = request.form.get('birth_year')

    try:
        birthday = datetime(int(birth_year), int(birth_month), int(birth_day))
    except (ValueError, TypeError):
        flash('Please enter a valid birth date')
        return redirect(url_for('auth.register'))

    # Validate username format
    if not USERNAME_PATTERN.match(username):
        flash('Username can only contain letters, numbers, and underscores (max 20 characters)')
        return redirect(url_for('auth.register'))

    # Validate password format
    if not PASSWORD_PATTERN.match(password):
        flash('Password must be between 8 and 200 characters and contain at least one uppercase letter, one lowercase letter, and one number')
        return redirect(url_for('auth.register'))

    # Validate gender
    if gender not in ['male', 'female']:
        flash('Please select a valid gender')
        return redirect(url_for('auth.register'))

    # Validate birthday
    today = datetime.utcnow()
    age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))

    if age < 5:
        flash('You must be at least 5 years old to register')
        return redirect(url_for('auth.register'))

    if age > 150:
        flash('Please enter a valid birth date')
        return redirect(url_for('auth.register'))

    if birthday > today:
        flash('Birth date cannot be in the future')
        return redirect(url_for('auth.register'))

    # Get preferences
    privacy_setting = request.form.get('privacy_setting', 'public')
    preferred_weight_unit = request.form.get('preferred_weight_unit', 'kg')
    preferred_distance_unit = request.form.get('preferred_distance_unit', 'km')
    preferred_measurement_unit = request.form.get('preferred_measurement_unit', 'cm')

    # Check if email or username already exists
    if User.query.filter_by(email=email).first():
        flash('Email address is already registered')
        return redirect(url_for('auth.register'))

    if User.query.filter_by(username=username).first():
        flash('Username is already taken')
        return redirect(url_for('auth.register'))

    # Create new user
    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        gender=gender,
        birthday=birthday,
        privacy_setting=privacy_setting,
        level=1,
        exp=0,
        preferred_weight_unit=preferred_weight_unit,
        preferred_distance_unit=preferred_distance_unit,
        preferred_measurement_unit=preferred_measurement_unit
    )
    new_user.set_password(password)

    try:
        # Add the user first
        db.session.add(new_user)
        db.session.flush()  # This gets us the user.id

        # Create initial bodyweight log
        initial_weight = Measurement(
            user_id=new_user.id,
            type='weight',
            value=weight_value,  # Already in kg
            unit='kg',
            date=datetime.utcnow()
        )
        db.session.add(initial_weight)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred during registration. Please try again.')
        return redirect(url_for('auth.register'))

@auth.route('/settings')
@login_required
def settings():
    # Calculate year range for the birthday dropdown
    current_year = datetime.utcnow().year
    year_range = YearRange(
        start=current_year - 150,  # Oldest possible age
        end=current_year - 5       # Minimum age requirement
    )
    return render_template('settings.html', year_range=year_range)

@auth.route('/update-preferences', methods=['POST'])
@login_required
def update_preferences():
    # Check if reset to defaults was requested
    if request.form.get('reset'):
        current_user.preferred_weight_unit = 'kg'
        current_user.preferred_distance_unit = 'km'
        current_user.preferred_measurement_unit = 'cm'
        current_user.range_enabled = True
        current_user.recommend_enabled = True
        db.session.commit()
        flash('Preferences reset to defaults', 'success')
        return redirect(url_for('auth.settings'))
    
    # Update user preferences
    current_user.preferred_weight_unit = request.form.get('preferred_weight_unit')
    current_user.preferred_distance_unit = request.form.get('preferred_distance_unit')
    current_user.preferred_measurement_unit = request.form.get('preferred_measurement_unit')
    
    # Handle checkbox values
    current_user.range_enabled = 'range_enabled' in request.form
    current_user.recommend_enabled = 'recommend_enabled' in request.form
    
    db.session.commit()
    flash('Preferences updated successfully', 'success')
    return redirect(url_for('auth.settings'))

@auth.route('/update-privacy', methods=['POST'])
@login_required
def update_privacy():
    privacy_setting = request.form.get('privacy_setting')
    if privacy_setting not in ['public', 'private']:
        flash('Invalid privacy setting', 'error')
        return redirect(url_for('auth.settings'))

    try:
        current_user.privacy_setting = privacy_setting
        db.session.commit()
        flash('Privacy settings updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating privacy settings', 'error')
        print(f"Error updating privacy settings: {str(e)}")  # For debugging

    return redirect(url_for('auth.settings'))

@auth.route('/change-username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form.get('new_username')

    # Validate username format
    if not USERNAME_PATTERN.match(new_username):
        flash('Username can only contain letters, numbers, and underscores (max 20 characters)', 'error')
        return redirect(url_for('auth.settings'))

    # Check if username is taken
    if User.query.filter_by(username=new_username).first():
        flash('This username is already taken', 'error')
        return redirect(url_for('auth.settings'))

    # Check if it's the same as current username
    if current_user.username == new_username:
        flash('This is already your current username', 'error')
        return redirect(url_for('auth.settings'))

    try:
        current_user.username = new_username
        db.session.commit()
        flash('Username successfully updated to: ' + new_username, 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating username', 'error')
        print(f"Error updating username: {str(e)}")  # For debugging

    return redirect(url_for('auth.settings'))

@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # Verify current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.settings'))

    # Validate new password format
    if not PASSWORD_PATTERN.match(new_password):
        flash('Password must be between 8 and 200 characters and contain at least one uppercase letter, one lowercase letter, and one number', 'error')
        return redirect(url_for('auth.settings'))

    # Confirm passwords match
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('auth.settings'))

    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating password', 'error')
        print(f"Error updating password: {str(e)}")  # For debugging

    return redirect(url_for('auth.settings'))

@auth.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    password = request.form.get('password')

    # Verify password
    if not current_user.check_password(password):
        flash('Incorrect password', 'error')
        return redirect(url_for('auth.settings'))

    try:
        user_id = current_user.id

        # Delete all related data first
        Measurement.query.filter_by(user_id=user_id).delete()
        Session.query.filter_by(user_id=user_id).delete()
        Workout.query.filter_by(user_id=user_id).delete()
        # Add any other related data deletions here

        # Now delete the user
        db.session.delete(current_user)
        db.session.commit()

        # Log out the user
        logout_user()

        flash('Your account has been permanently deleted', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting account: {str(e)}")  # For debugging
        db.session.rollback()
        flash('An error occurred while deleting your account', 'error')
        return redirect(url_for('auth.settings'))

@auth.route('/update-personal-info', methods=['POST'])
@login_required
def update_personal_info():
    """Update user's personal information and preferences"""
    # Extract form data
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    gender = request.form.get('gender')
    birthday = request.form.get('birthday')
    
    # Get current user
    user = User.query.get(current_user.id)
    
    # Update user information
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    
    # Validate email - check if it's already in use by another user
    if email and email != user.email:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Email already in use by another account', 'error')
            return redirect(url_for('auth.settings'))
        user.email = email
    
    # Update gender if specified
    if gender and gender in ['male', 'female', 'other', 'prefer_not_to_say']:
        user.gender = gender
    
    # Update birthday if specified
    if birthday:
        try:
            user.birthday = datetime.strptime(birthday, '%Y-%m-%d')
        except ValueError:
            flash('Invalid birthday format', 'error')
            return redirect(url_for('auth.settings'))
    
    # Save changes
    db.session.commit()
    
    flash('Personal information updated successfully', 'success')
    return redirect(url_for('auth.settings'))

@auth.route('/start-workout')
@login_required
def start_workout():
    """Start a new workout session"""
    # Get all exercises for the user to select from
    exercises = Exercise.query.filter_by(user_created=False).order_by(Exercise.name).all()
    
    # Add user-created exercises
    user_exercises = Exercise.query.filter_by(user_created=True, created_by=current_user.id).order_by(Exercise.name).all()
    exercises.extend(user_exercises)
    
    # Define sort_key function
    def sort_key(exercise):
        return exercise.name if exercise and hasattr(exercise, 'name') else ""
    
    # Sort exercises alphabetically
    exercises.sort(key=sort_key)
    
    # Get user's current bodyweight for bodyweight exercises
    bodyweight = None
    bodyweight_log = Measurement.query.filter_by(user_id=current_user.id, type='weight').order_by(Measurement.date.desc()).first()
    if bodyweight_log:
        bodyweight = bodyweight_log.value
    
    # Get the unread notification count for the notification badge
    unread_notification_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('workout/start.html', 
                          exercises=exercises, 
                          user_weight=bodyweight,
                          unread_notification_count=unread_notification_count)