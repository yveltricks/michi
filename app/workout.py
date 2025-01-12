# Create this file at "app/workout.py"

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import Exercise, Session, User
from .models import Exercise, Session, User, BodyweightLog  # Add BodyweightLog here
from . import db
import json
from datetime import datetime

workout = Blueprint('workout', __name__)

@workout.route('/start-workout')
@login_required
def start_workout():
    """
    # This route shows the workout creation page where users can
    # select exercises and start logging their workout
    """
    # Get all available exercises
    exercises = Exercise.query.all()
    return render_template('workout/start.html', exercises=exercises)

@workout.route('/log-workout', methods=['POST'])
@login_required
def log_workout():
    data = request.get_json()

    # Calculate total workout volume and duration (only for completed sets)
    total_volume = 0
    exercises_data = data.get('exercises', [])

    # Format exercises for better display
    formatted_exercises = []
    for exercise in exercises_data:
        # Only include exercises with completed sets
        completed_sets = [set for set in exercise['sets'] if set.get('completed', False)]
        if completed_sets:
            formatted_exercises.append({
                'name': exercise['name'],
                'sets': len(completed_sets)  # Only count completed sets
            })
            
            # Calculate volume only for completed sets
            exercise_volume = sum(
                set['weight'] * set['reps']
                for set in completed_sets
                if 'weight' in set and 'reps' in set
            )
            total_volume += exercise_volume

    # Create new session with formatted exercise data
    new_session = Session(
        user_id=current_user.id,
        session_date=datetime.utcnow(),
        duration=f"{data.get('duration', 0)} minutes",
        volume=total_volume,
        exercises=json.dumps(formatted_exercises),
        exp_gained=len(formatted_exercises) * 50,  # Only count exercises with completed sets
        session_rating=data.get('rating', 5),
        title=data.get('title', 'Workout'),
        description=data.get('description', ''),
        photo=data.get('photo_url', None)
    )

    # Update user's exp
    current_user.exp += new_session.exp_gained
    current_user.update_level()

    db.session.add(new_session)
    db.session.commit()

    return jsonify({
        'success': True,
        'session_id': new_session.id,
        'exp_gained': new_session.exp_gained
    })

@workout.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """
    # This route shows the detailed view of a completed workout session
    # It includes all exercise data, stats, and progress comparisons
    """
    session = Session.query.get_or_404(session_id)
    
    # Check if user has permission to view this session
    if session.user.privacy_setting == 'private' and session.user_id != current_user.id:
        flash('You do not have permission to view this session.')
        return redirect(url_for('auth.home'))
        
    exercises = json.loads(session.exercises) if session.exercises else []
    
    return render_template('workout/view_session.html', 
                         session=session, 
                         exercises=exercises)

@workout.route('/api/exercises')
@login_required
def get_exercises():
    exercises = Exercise.query.all()
    return jsonify([{
        'id': e.id,
        'name': e.name,
        'muscles_worked': e.muscles_worked
    } for e in exercises])

@workout.route('/log-bodyweight', methods=['POST'])
@login_required
def log_bodyweight():
    weight = request.json.get('weight')
    if not weight or weight <= 0:
        return jsonify({'success': False, 'error': 'Invalid weight'}), 400
        
    log = BodyweightLog(user_id=current_user.id, weight=weight)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'success': True})

@workout.route('/bodyweight-history')
@login_required
def bodyweight_history():
    logs = BodyweightLog.query.filter_by(user_id=current_user.id)\
        .order_by(BodyweightLog.date.desc()).all()
    return render_template('workout/bodyweight_history.html', logs=logs)

@workout.route('/bodyweight-tracking')
@login_required
def bodyweight_tracking():
    # Get user's bodyweight logs ordered by date
    logs = BodyweightLog.query.filter_by(user_id=current_user.id)\
        .order_by(BodyweightLog.date.desc()).all()
    return render_template('workout/bodyweight.html', weight_logs=logs)

@workout.route('/delete-weight/<int:log_id>', methods=['DELETE'])
@login_required
def delete_weight(log_id):
    log = BodyweightLog.query.get_or_404(log_id)
    
    # Check if the log belongs to the current user
    if log.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500