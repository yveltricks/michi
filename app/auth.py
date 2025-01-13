# This handles all my authentication routes (login, register, etc.)
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Session, BodyweightLog 
from sqlalchemy import desc
from . import db
from datetime import datetime  # Added this for utcnow()
import re

auth = Blueprint('auth', __name__)

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
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    privacy_setting = request.form.get('privacy_setting', 'public')
    
    # Get unit preferences
    preferred_weight_unit = request.form.get('preferred_weight_unit', 'kg')
    preferred_distance_unit = request.form.get('preferred_distance_unit', 'km')
    preferred_measurement_unit = request.form.get('preferred_measurement_unit', 'cm')
    
    # Get bodyweight and its unit
    bodyweight = request.form.get('bodyweight')
    weight_unit = request.form.get('weight_unit', 'kg')

    # Validate the bodyweight
    try:
        bodyweight = float(bodyweight)
        if bodyweight <= 0:
            flash('Please enter a valid body weight')
            return redirect(url_for('auth.register'))
            
        # Convert weight to kg if entered in lbs
        if weight_unit == 'lbs':
            bodyweight = bodyweight * 0.45359237  # Convert lbs to kg
            
    except (ValueError, TypeError):
        flash('Please enter a valid body weight')
        return redirect(url_for('auth.register'))

    if User.query.filter_by(email=email).first():
        flash('Email already exists')
        return redirect(url_for('auth.register'))
        
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('auth.register'))
        
    if len(password) < 8:
        flash('Password must be at least 8 characters long')
        return redirect(url_for('auth.register'))

    # Create new user with unit preferences
    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        privacy_setting=privacy_setting,
        level=1,
        exp=0,
        preferred_weight_unit=preferred_weight_unit,
        preferred_distance_unit=preferred_distance_unit,
        preferred_measurement_unit=preferred_measurement_unit
    )
    new_user.set_password(password)

    # Add the user first
    db.session.add(new_user)
    db.session.flush()  # This gets us the user.id

    # Create initial bodyweight log (always stored in kg)
    initial_weight = BodyweightLog(
        user_id=new_user.id,
        weight=bodyweight,  # Already converted to kg if needed
        date=datetime.utcnow()
    )
    db.session.add(initial_weight)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('An error occurred. Please try again.')
        return redirect(url_for('auth.register'))

    return redirect(url_for('auth.login'))

@auth.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

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
    except:
        db.session.rollback()
        flash('Error updating preferences', 'error')
    
    return redirect(url_for('auth.settings'))

@auth.route('/update-privacy', methods=['POST'])
@login_required
def update_privacy():
    current_user.privacy_setting = request.form.get('privacy_setting', 'public')
    
    try:
        db.session.commit()
        flash('Privacy settings updated successfully!', 'success')
    except:
        db.session.rollback()
        flash('Error updating privacy settings', 'error')
    
    return redirect(url_for('auth.settings'))


    
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,20}$')

@auth.route('/change-username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form.get('new_username')
    
    # Validate username format
    if not USERNAME_PATTERN.match(new_username):
        flash('Username can only contain letters, numbers, and underscores (max 20 characters)')
        return redirect(url_for('auth.settings'))
    
    # Check if username is taken
    if User.query.filter_by(username=new_username).first():
        flash('Username already taken')
        return redirect(url_for('auth.settings'))
    
    try:
        current_user.username = new_username
        db.session.commit()
        flash('Username updated successfully!', 'success')
    except:
        db.session.rollback()
        flash('Error updating username', 'error')
    
    return redirect(url_for('auth.settings'))

@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect')
        return redirect(url_for('auth.settings'))
    
    # Validate new password
    if len(new_password) < 8 or len(new_password) > 60:
        flash('Password must be between 8 and 60 characters')
        return redirect(url_for('auth.settings'))
    
    # Confirm passwords match
    if new_password != confirm_password:
        flash('New passwords do not match')
        return redirect(url_for('auth.settings'))
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password updated successfully!', 'success')
    except:
        db.session.rollback()
        flash('Error updating password', 'error')
    
    return redirect(url_for('auth.settings'))

@auth.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    password = request.form.get('password')
    
    # Verify password
    if not current_user.check_password(password):
        flash('Incorrect password')
        return redirect(url_for('auth.settings'))
    
    try:
        # Check if user has more than one bodyweight log
        if len(current_user.bodyweight_logs) <= 1:
            flash('You must have at least one weight logged at all times')
            return redirect(url_for('auth.settings'))
        
        # Delete all related data
        Session.query.filter_by(user_id=current_user.id).delete()
        BodyweightLog.query.filter_by(user_id=current_user.id).delete()
        # Add other model deletions here as needed
        
        user_id = current_user.id
        logout_user()  # Log out before deleting
        
        # Delete the user
        User.query.filter_by(id=user_id).delete()
        db.session.commit()
        
        flash('Your account has been deleted successfully', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash('Error deleting account', 'error')
        return redirect(url_for('auth.settings'))