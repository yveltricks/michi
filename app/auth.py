from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Session, Measurement
from sqlalchemy import desc
from . import db
from datetime import datetime, timedelta
from dataclasses import dataclass
import re

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
    # Get the current user's sessions and sessions from people they follow
    following_ids = [user.id for user in current_user.following]
    following_ids.append(current_user.id)  # Include current user's sessions

    sessions = Session.query\
        .filter(Session.user_id.in_(following_ids))\
        .order_by(desc(Session.session_date))\
        .limit(10)\
        .all()

    return render_template('home.html', sessions=sessions)

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
    if request.form.get('reset') == 'true':
        # Reset to defaults
        current_user.preferred_weight_unit = 'kg'
        current_user.preferred_distance_unit = 'km'
        current_user.preferred_measurement_unit = 'cm'
        flash('Preferences reset to defaults!', 'success')
    else:
        # Update with new preferences
        current_user.preferred_weight_unit = request.form.get('preferred_weight_unit', 'kg')
        current_user.preferred_distance_unit = request.form.get('preferred_distance_unit', 'km')
        current_user.preferred_measurement_unit = request.form.get('preferred_measurement_unit', 'cm')
        flash('Preferences updated successfully!', 'success')

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Error updating preferences', 'error')
        print(f"Error updating preferences: {str(e)}")  # For debugging

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

# New route for updating personal information
@auth.route('/update-personal-info', methods=['POST'])
@login_required
def update_personal_info():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    gender = request.form.get('gender')

    # Get birthday components
    try:
        birth_day = int(request.form.get('birth_day'))
        birth_month = int(request.form.get('birth_month'))
        birth_year = int(request.form.get('birth_year'))
    except (ValueError, TypeError):
        flash('Please enter valid date values', 'error')
        return redirect(url_for('auth.settings'))

    # Validate gender
    if gender not in ['male', 'female']:
        flash('Please select a valid gender', 'error')
        return redirect(url_for('auth.settings'))

    # Validate birthday
    try:
        birthday = datetime(birth_year, birth_month, birth_day)

        # Validate age range
        today = datetime.utcnow()
        age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))

        if age < 5:
            flash('You must be at least 5 years old', 'error')
            return redirect(url_for('auth.settings'))
        if age > 150:
            flash('Please enter a valid birth date', 'error')
            return redirect(url_for('auth.settings'))
        if birthday > today:
            flash('Birth date cannot be in the future', 'error')
            return redirect(url_for('auth.settings'))

    except ValueError:
        flash('Invalid date. Please check the day matches the selected month.', 'error')
        return redirect(url_for('auth.settings'))

    try:
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.gender = gender
        current_user.birthday = birthday
        db.session.commit()
        flash('Personal information updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating personal information', 'error')
        print(f"Error updating personal info: {str(e)}")  # For debugging

    return redirect(url_for('auth.settings'))