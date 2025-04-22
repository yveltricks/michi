from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Session, Measurement, Workout, Exercise, WorkoutLike, WorkoutComment, Notification, Set
from sqlalchemy import desc
from . import db
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
import json
from .workout import calculate_workout_metrics  # Import the function from workout.py
from .utils import convert_volume_to_preferred_unit, calculate_weekly_stats, compare_exercise_progress
from werkzeug.utils import secure_filename
import os

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
    """Home page route"""
    # Get recent workouts
    recent_workouts = Workout.query.filter_by(user_id=current_user.id).order_by(Workout.date.desc()).limit(10).all()
    
    # Get followed users' workouts
    followed_users = current_user.following.all()
    followed_user_ids = [user.id for user in followed_users]
    followed_workouts = Workout.query.filter(Workout.user_id.in_(followed_user_ids)).order_by(Workout.date.desc()).limit(10).all()
    
    # Get recent sessions (completed workouts)
    recent_sessions = Session.query.filter_by(user_id=current_user.id).order_by(Session.session_date.desc()).limit(10).all()
    
    # Calculate weekly stats
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
    
    # Process recent sessions first
    for session in recent_sessions:
        try:
            # Get all sets for this session
            sets = Set.query.filter_by(session_id=session.id).all()
            
            # Group sets by exercise
            exercise_sets = {}
            for s in sets:
                if s.exercise_id not in exercise_sets:
                    exercise_sets[s.exercise_id] = []
                exercise_sets[s.exercise_id].append(s)
            
            # Format exercises
            exercises = []
            for exercise_id, sets_list in exercise_sets.items():
                exercise = Exercise.query.get(exercise_id)
                if not exercise:
                    continue
                
                # Compare this exercise with the previous session's performance
                comparison = 0  # Default to no change
                try:
                    comparison = compare_exercise_progress(session.id, current_user.id)
                    if exercise_id in comparison:
                        comparison = comparison[exercise_id]
                    else:
                        comparison = 0
                except Exception as e:
                    print(f"Error in exercise comparison: {e}")
                    comparison = 0
                
                exercises.append({
                    'id': exercise_id,
                    'name': exercise.name,
                    'sets_count': len(sets_list),
                    'comparison': comparison
                })
            
            # Get like count
            like_count = WorkoutLike.query.filter_by(workout_id=session.id).count()
            
            # Check if current user has liked this workout
            user_liked = WorkoutLike.query.filter_by(
                workout_id=session.id, 
                user_id=current_user.id
            ).first() is not None
            
            # Get comment count
            comment_count = WorkoutComment.query.filter_by(workout_id=session.id).count()
            
            # Get user level
            user_level = current_user.level
            
            combined_sessions.append({
                'id': session.id,
                'session_date': session.session_date,
                'title': session.title,
                'description': session.description,
                'exercises': exercises,
                'user': current_user,
                'is_own': True,
                'duration': session.duration,
                'volume': convert_volume_to_preferred_unit(session.volume, current_user.preferred_weight_unit),
                'session_rating': session.session_rating,
                'like_count': like_count,
                'user_liked': user_liked,
                'comment_count': comment_count,
                'user_level': user_level,
                'photo': session.photo
            })
        except Exception as e:
            print(f"Error processing recent session: {e}")
            continue
    
    # Sort combined sessions by date
    combined_sessions.sort(key=lambda x: x['session_date'], reverse=True)
    
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

@auth.route('/update-profile-pic', methods=['POST'])
@login_required
def update_profile_pic():
    """Update or remove user's profile picture"""
    try:
        print("Starting profile picture update...")
        
        # Check if user wants to remove their profile picture
        if 'remove' in request.form:
            print("Removing profile picture...")
            # Store old profile pic path for cleanup
            old_pic = current_user.profile_pic
            
            # Update database first
            current_user.profile_pic = None
            db.session.commit()
            
            # Try to remove the old file if it exists
            if old_pic and os.path.isabs(old_pic):
                try:
                    # Get the full path from the absolute URL path
                    file_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        old_pic.lstrip('/')
                    )
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed old profile picture: {file_path}")
                except Exception as e:
                    print(f"Error removing old picture file: {str(e)}")
            
            flash('Profile picture removed successfully', 'success')
            return redirect(url_for('auth.settings'))
        
        # Check if a file was uploaded
        if 'profile_pic' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('auth.settings'))
        
        file = request.files['profile_pic']
        
        # Check if file is empty
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('auth.settings'))
        
        # Check if file is allowed
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not '.' in file.filename or file.filename.split('.')[-1].lower() not in allowed_extensions:
            flash('Only image files (PNG, JPG, JPEG, GIF) are allowed', 'error')
            return redirect(url_for('auth.settings'))
        
        # Create uploads directory - IMPORTANT: Use app/static/uploads for web access
        upload_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static',
            'uploads'
        )
        os.makedirs(upload_dir, exist_ok=True)
        print(f"Upload directory: {upload_dir}")
        
        # Generate unique filename
        import uuid
        filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save the new file
        file.save(file_path)
        print(f"Saved new profile picture to: {file_path}")
        
        # Set the URL path that will work in the browser
        # This should match where the files are actually being saved
        url_path = url_for('static', filename=f'uploads/{filename}')
        print(f"Setting profile_pic in database to: {url_path}")
        
        current_user.profile_pic = url_path
        db.session.commit()
        
        flash('Profile picture updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error in profile picture update: {str(e)}")
        flash(f'Error updating profile picture: {str(e)}', 'error')
    
    return redirect(url_for('auth.settings'))

@auth.route('/profile')
@auth.route('/profile/<username>')
@login_required
def profile(username=None):
    """
    User profile page.
    If username is not provided, show the current user's profile.
    """
    if username is None:
        user = current_user
    else:
        user = User.query.filter_by(username=username).first_or_404()
    
    # Get workout count
    workout_count = Workout.query.filter_by(user_id=user.id).count()
    
    # Get follower and following count
    follower_count = user.followers.count()
    following_count = user.following.count()
    
    # Calculate weekly stats
    weekly_stats = calculate_weekly_stats(user.id)
    
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
    
    # Get user activity for the last 3 months
    three_months_ago = datetime.now() - timedelta(days=90)
    
    # Get data for volume chart
    volume_data = db.session.query(
        db.func.strftime('%Y-%m-%d', Session.session_date).label('date'),
        db.func.sum(Session.volume).label('volume')
    ).filter(
        Session.user_id == user.id,
        Session.session_date >= three_months_ago
    ).group_by('date').order_by('date').all()
    
    # Get data for duration chart
    duration_data = db.session.query(
        db.func.strftime('%Y-%m-%d', Session.session_date).label('date'),
        db.func.sum(db.func.coalesce(Session.duration, '0')).label('duration')
    ).filter(
        Session.user_id == user.id,
        Session.session_date >= three_months_ago
    ).group_by('date').order_by('date').all()
    
    # Get data for reps chart
    reps_data = db.session.query(
        db.func.strftime('%Y-%m-%d', Session.session_date).label('date'),
        db.func.sum(Session.total_reps).label('reps')
    ).filter(
        Session.user_id == user.id,
        Session.session_date >= three_months_ago
    ).group_by('date').order_by('date').all()
    
    # Get data for EXP chart
    exp_data = db.session.query(
        db.func.strftime('%Y-%m-%d', Session.session_date).label('date'),
        db.func.sum(Session.exp_gained).label('exp')
    ).filter(
        Session.user_id == user.id,
        Session.session_date >= three_months_ago
    ).group_by('date').order_by('date').all()
    
    # Format chart data for JavaScript
    chart_data = {
        'dates': [str(date) for date, _ in volume_data],
        'volume': [float(volume) for _, volume in volume_data],
        'duration': [float(duration) for _, duration in duration_data],
        'reps': [int(reps) if reps else 0 for _, reps in reps_data],
        'exp': [int(exp) if exp else 0 for _, exp in exp_data]
    }
    
    # Get user's recent workouts
    recent_workouts = Session.query.filter_by(user_id=user.id).order_by(Session.session_date.desc()).limit(5).all()
    
    # Process each workout to get additional data
    processed_workouts = []
    
    for session in recent_workouts:
        try:
            # Get all sets for this session
            sets = Set.query.filter_by(session_id=session.id).all()
            
            # Group sets by exercise
            exercise_sets = {}
            for s in sets:
                if s.exercise_id not in exercise_sets:
                    exercise_sets[s.exercise_id] = []
                exercise_sets[s.exercise_id].append(s)
            
            # Format exercises
            exercises = []
            for exercise_id, sets_list in exercise_sets.items():
                exercise = Exercise.query.get(exercise_id)
                if not exercise:
                    continue
                
                # Compare this exercise with the previous session's performance
                comparison = 0  # Default to no change
                try:
                    comparison = compare_exercise_progress(session.id, user.id)
                    if exercise_id in comparison:
                        comparison = comparison[exercise_id]
                    else:
                        comparison = 0
                except Exception as e:
                    print(f"Error in exercise comparison: {e}")
                    comparison = 0
                
                exercises.append({
                    'id': exercise_id,
                    'name': exercise.name,
                    'sets_count': len(sets_list),
                    'comparison': comparison
                })
            
            # Get like count
            like_count = WorkoutLike.query.filter_by(workout_id=session.id).count()
            
            # Check if current user has liked this workout
            user_liked = WorkoutLike.query.filter_by(
                workout_id=session.id, 
                user_id=current_user.id
            ).first() is not None
            
            # Get comment count
            comment_count = WorkoutComment.query.filter_by(workout_id=session.id).count()
            
            processed_workouts.append({
                'id': session.id,
                'session_date': session.session_date,
                'title': session.title,
                'description': session.description,
                'exercises': exercises,
                'user': user,
                'is_own': user.id == current_user.id,
                'duration': session.duration,
                'volume': convert_volume_to_preferred_unit(session.volume, user.preferred_weight_unit),
                'session_rating': session.session_rating,
                'like_count': like_count,
                'user_liked': user_liked,
                'comment_count': comment_count,
                'user_level': user.level,
                'photo': session.photo
            })
        except Exception as e:
            print(f"Error processing workout: {e}")
            continue
    
    # Get unread notification count
    unread_notification_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    # Get best lifts
    best_lifts = {}
    
    # Find all exercises with input_type containing 'weight' and 'reps'
    weight_reps_exercises = Exercise.query.filter(
        Exercise.input_type.like('%weight%'),
        Exercise.input_type.like('%reps%')
    ).all()
    
    for exercise in weight_reps_exercises:
        # Find the highest weight for this exercise
        best_set = Set.query.join(Session).filter(
            Set.exercise_id == exercise.id,
            Session.user_id == user.id,
            Session.session_date >= three_months_ago
        ).order_by(Set.weight.desc()).first()
        
        if best_set and best_set.weight > 0:
            best_lifts[exercise.name] = f"{convert_volume_to_preferred_unit(best_set.weight, user.preferred_weight_unit)}{user.preferred_weight_unit}"
    
    # Calculate user account age
    account_age = (datetime.now() - user.created_at).days if user.created_at else 0
    
    # Format account age in a human-readable way
    if account_age == 0:
        account_age_str = "today"
    elif account_age == 1:
        account_age_str = "yesterday"
    elif account_age < 30:
        account_age_str = f"{account_age} days ago"
    elif account_age < 365:
        months = account_age // 30
        account_age_str = f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = account_age // 365
        account_age_str = f"{years} year{'s' if years > 1 else ''} ago"
    
    return render_template('profile.html',
                          user=user,
                          workout_count=workout_count,
                          follower_count=follower_count,
                          following_count=following_count,
                          weekly_stats=weekly_stats,
                          chart_data=chart_data,
                          workouts=processed_workouts,
                          unread_notification_count=unread_notification_count,
                          best_lifts=best_lifts,
                          account_age=account_age,
                          account_age_str=account_age_str)

@auth.route('/statistics')
@login_required
def statistics():
    """User statistics page"""
    user = current_user
    
    # Calculate yearly stats
    this_year_start = datetime(datetime.now().year, 1, 1)
    
    # Workout count for this year
    yearly_workout_count = Session.query.filter(
        Session.user_id == user.id,
        Session.session_date >= this_year_start
    ).count()
    
    # Total EXP gained this year
    yearly_exp = db.session.query(db.func.sum(Session.exp_gained)).filter(
        Session.user_id == user.id,
        Session.session_date >= this_year_start
    ).scalar() or 0
    
    # Total levels gained this year (approximation)
    yearly_levels = yearly_exp // 100
    
    # Total workout duration this year
    total_duration_seconds = db.session.query(db.func.sum(db.func.extract('epoch', db.func.cast(Session.duration, db.Time)))).filter(
        Session.user_id == user.id,
        Session.session_date >= this_year_start
    ).scalar() or 0
    
    # Format duration as days, hours, minutes
    days = total_duration_seconds // (24 * 3600)
    remaining_seconds = total_duration_seconds % (24 * 3600)
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    
    yearly_duration = f"{days}d {hours}h {minutes}m"
    
    # Total weight lifted this year
    yearly_volume = db.session.query(db.func.sum(Session.volume)).filter(
        Session.user_id == user.id,
        Session.session_date >= this_year_start
    ).scalar() or 0
    
    # Format volume with the user's preferred unit
    yearly_volume_formatted = f"{convert_volume_to_preferred_unit(yearly_volume, user.preferred_weight_unit)} {user.preferred_weight_unit}"
    
    # Get best lifts for all weight+reps exercises
    best_lifts = {}
    
    # Find all exercises with input_type containing 'weight' and 'reps'
    weight_reps_exercises = Exercise.query.filter(
        Exercise.input_type.like('%weight%'),
        Exercise.input_type.like('%reps%')
    ).all()
    
    for exercise in weight_reps_exercises:
        # Find the highest weight for this exercise
        best_set = Set.query.join(Session).filter(
            Set.exercise_id == exercise.id,
            Session.user_id == user.id,
            Session.session_date >= this_year_start
        ).order_by(Set.weight.desc()).first()
        
        if best_set and best_set.weight > 0:
            best_lifts[exercise.name] = f"{convert_volume_to_preferred_unit(best_set.weight, user.preferred_weight_unit)}{user.preferred_weight_unit}"
    
    # All-time stats (mostly the same as yearly stats for now)
    all_time_workout_count = Session.query.filter(Session.user_id == user.id).count()
    all_time_exp = db.session.query(db.func.sum(Session.exp_gained)).filter(Session.user_id == user.id).scalar() or 0
    all_time_levels = all_time_exp // 100
    
    # Total all-time workout duration
    all_time_duration_seconds = db.session.query(db.func.sum(db.func.extract('epoch', db.func.cast(Session.duration, db.Time)))).filter(
        Session.user_id == user.id
    ).scalar() or 0
    
    # Format duration as days, hours, minutes
    days = all_time_duration_seconds // (24 * 3600)
    remaining_seconds = all_time_duration_seconds % (24 * 3600)
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    
    all_time_duration = f"{days}d {hours}h {minutes}m"
    
    # Total all-time weight lifted
    all_time_volume = db.session.query(db.func.sum(Session.volume)).filter(Session.user_id == user.id).scalar() or 0
    all_time_volume_formatted = f"{convert_volume_to_preferred_unit(all_time_volume, user.preferred_weight_unit)} {user.preferred_weight_unit}"
    
    # Get best all-time lifts for all weight+reps exercises
    all_time_best_lifts = {}
    
    for exercise in weight_reps_exercises:
        # Find the highest weight for this exercise
        best_set = Set.query.join(Session).filter(
            Set.exercise_id == exercise.id,
            Session.user_id == user.id
        ).order_by(Set.weight.desc()).first()
        
        if best_set and best_set.weight > 0:
            all_time_best_lifts[exercise.name] = f"{convert_volume_to_preferred_unit(best_set.weight, user.preferred_weight_unit)}{user.preferred_weight_unit}"
    
    # Get unread notification count
    unread_notification_count = Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).count()
    
    return render_template('statistics.html',
                          yearly_workout_count=yearly_workout_count,
                          yearly_exp=yearly_exp,
                          yearly_levels=yearly_levels,
                          yearly_duration=yearly_duration,
                          yearly_volume=yearly_volume_formatted,
                          best_lifts=best_lifts,
                          all_time_workout_count=all_time_workout_count,
                          all_time_exp=all_time_exp,
                          all_time_levels=all_time_levels,
                          all_time_duration=all_time_duration,
                          all_time_volume=all_time_volume_formatted,
                          all_time_best_lifts=all_time_best_lifts,
                          unread_notification_count=unread_notification_count)

@auth.route('/calendar')
@login_required
def calendar():
    """Activity calendar showing workout days"""
    user = current_user
    
    # Get all workout dates for the past year
    one_year_ago = datetime.now() - timedelta(days=365)
    workouts = Session.query.filter(
        Session.user_id == user.id,
        Session.session_date >= one_year_ago
    ).all()
    
    # Create calendar data
    calendar_data = {}
    
    for workout in workouts:
        date_str = workout.session_date.strftime('%Y-%m-%d')
        if date_str not in calendar_data:
            calendar_data[date_str] = {
                'count': 1,
                'volume': workout.volume,
                'exp': workout.exp_gained
            }
        else:
            calendar_data[date_str]['count'] += 1
            calendar_data[date_str]['volume'] += workout.volume
            calendar_data[date_str]['exp'] += workout.exp_gained
    
    # Get unread notification count
    unread_notification_count = Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).count()
    
    # Get current year for calendar initialization
    current_year = datetime.now().year
    
    return render_template('calendar.html',
                          calendar_data=calendar_data,
                          current_year=current_year,
                          unread_notification_count=unread_notification_count)

@auth.route('/user/<int:user_id>/follow', methods=['POST'])
@login_required
def follow_user(user_id):
    """Follow or unfollow a user"""
    # Check if user exists
    user = User.query.get_or_404(user_id)
    
    # Don't allow following yourself
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'You cannot follow yourself'
        }), 400
    
    # Check if already following
    is_following = current_user.is_following(user)
    
    if is_following:
        # Unfollow
        current_user.following.remove(user)
        db.session.commit()
        return jsonify({
            'success': True,
            'following': False,
            'follower_count': user.followers.count(),
            'message': f'You unfollowed {user.username}'
        })
    else:
        # Follow
        current_user.following.append(user)
        db.session.commit()
        
        # Create notification for the followed user
        notification = Notification(
            user_id=user.id,
            message=f"{current_user.username} started following you!",
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'following': True,
            'follower_count': user.followers.count(),
            'message': f'You are now following {user.username}'
        })