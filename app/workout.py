from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import Exercise, Session, User, Measurement, Set
from . import db
import json
from datetime import datetime, timedelta

workout = Blueprint('workout', __name__)

@workout.route('/start-workout')
@login_required
def start_workout():
    """
    This route shows the workout creation page where users can
    select exercises and start logging their workout.
    """
    # Get all available exercises
    exercises = Exercise.query.all()
    return render_template('workout/start.html', exercises=exercises)

@workout.route('/log-workout', methods=['POST'])
@login_required
def log_workout():
    data = request.get_json()
    exercises_data = data.get('exercises', [])

    # Get user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
        .order_by(Measurement.date.desc()).first()
    bodyweight = latest_bodyweight.value if latest_bodyweight else None

    # Create new session
    new_session = Session(
        user_id=current_user.id,
        session_date=datetime.utcnow(),
        duration=f"{data.get('duration', 0)} minutes",
        title=data.get('title', 'Workout'),
        description=data.get('description', ''),
        session_rating=data.get('rating', 5),
        photo=data.get('photo_url', None)
    )
    db.session.add(new_session)
    db.session.flush()  # Get new_session.id

    total_volume = 0
    formatted_exercises = []

    # Process each exercise and its sets
    for exercise_data in exercises_data:
        exercise = Exercise.query.get(exercise_data['id'])
        if not exercise:
            continue

        completed_sets = [set for set in exercise_data['sets'] if set.get('completed', False)]
        if not completed_sets:
            continue

        formatted_exercises.append({
            'name': exercise.name,
            'sets': len(completed_sets)
        })

        # Create Set records and calculate volume
        for set_idx, set_data in enumerate(completed_sets):
            set_volume = exercise.calculate_volume(set_data, bodyweight)
            total_volume += set_volume

            # Create new Set record with all fields
            new_set = Set(
                exercise_id=exercise.id,
                session_id=new_session.id,
                completed=True,
                order=set_idx,
                set_type=set_data.get('set_type', 'normal')
            )

            # Add all relevant fields based on exercise type
            for field in exercise.get_input_fields():
                setattr(new_set, field, set_data.get(field, 0))

            db.session.add(new_set)

    # Update session with total volume and exercise data
    new_session.volume = total_volume
    new_session.exercises = json.dumps(formatted_exercises)
    new_session.exp_gained = len(formatted_exercises) * 50

    # Update user's exp
    current_user.exp += new_session.exp_gained
    current_user.update_level()

    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'session_id': new_session.id,
            'exp_gained': new_session.exp_gained
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workout.route('/api/previous-values/<int:exercise_id>')
@login_required
def get_previous_values(exercise_id):
    # Get the last completed session that has this exercise with completed sets
    subquery = db.session.query(Session.id)\
        .join(Set)\
        .filter(
            Session.user_id == current_user.id,
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Session.session_date.desc())\
        .limit(1)\
        .subquery()

    previous_sets = Set.query\
        .filter(
            Set.session_id.in_(subquery),
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Set.order)\
        .all()

    # Add some debug logging
    print(f"Found {len(previous_sets)} previous sets for exercise {exercise_id}")
    for set in previous_sets:
        print(f"Set {set.order + 1}: {set.weight}kg x {set.reps} reps")

    return jsonify([{
        'weight': set.weight,
        'reps': set.reps,
        'order': set.order
    } for set in previous_sets])

@workout.route('/api/previous-values/<int:exercise_id>/<int:set_number>')
@login_required
def get_specific_previous_value(exercise_id, set_number):
    # Get the last completed session that has this exercise with completed sets
    subquery = db.session.query(Session.id)\
        .join(Set)\
        .filter(
            Session.user_id == current_user.id,
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Session.session_date.desc())\
        .limit(1)\
        .subquery()

    previous_set = Set.query\
        .filter(
            Set.session_id.in_(subquery),
            Set.exercise_id == exercise_id,
            Set.order == set_number - 1,  # Convert to 0-based index
            Set.completed == True
        )\
        .first()

    if not previous_set:
        print(f"No previous set found for exercise {exercise_id}, set number {set_number}")
        return jsonify(None)

    print(f"Found previous set: {previous_set.weight}kg x {previous_set.reps} reps")
    return jsonify({
        'weight': previous_set.weight,
        'reps': previous_set.reps
    })

@workout.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """
    This route shows the detailed view of a completed workout session.
    It includes all exercise data, stats, and progress comparisons.
    """
    session = Session.query.get_or_404(session_id)

    # Check if user has permission to view this session
    if session.user.privacy_setting == 'private' and session.user_id != current_user.id:
        flash('You do not have permission to view this session.')
        return redirect(url_for('auth.home'))

    exercises = json.loads(session.exercises) if session.exercises else []

    return render_template('workout/view_session.html', session=session, exercises=exercises)

@workout.route('/api/exercises')
@login_required
def get_exercises():
    exercises = Exercise.query.all()
    return jsonify([{
        'id': e.id,
        'name': e.name,
        'muscles_worked': e.muscles_worked
    } for e in exercises])

@workout.route('/api/exercise-details/<int:exercise_id>')
@login_required
def get_exercise_details(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)

    # Get user's latest bodyweight if needed for calculations
    latest_bodyweight = None
    if exercise.input_type in ['bodyweight_reps', 'weighted_bodyweight', 'assisted_bodyweight']:
        bodyweight_log = Measurement.query.filter_by(user_id=current_user.id, type='weight')\
            .order_by(Measurement.date.desc()).first()
        if bodyweight_log:
            latest_bodyweight = bodyweight_log.value

    # Get previous values
    previous_set = Set.query\
        .join(Session)\
        .filter(
            Session.user_id == current_user.id,
            Set.exercise_id == exercise_id,
            Set.completed == True
        )\
        .order_by(Session.session_date.desc())\
        .first()

    return jsonify({
        'input_type': exercise.input_type,
        'units': exercise.get_units(),
        'fields': exercise.get_input_fields(),
        'latest_bodyweight': latest_bodyweight,
        'previousValues': previous_set.to_dict() if previous_set else None
    })

@workout.route('/measurements')
@login_required
def measurements():
    """Render the measurements landing page."""
    # Pass the Measurement class to the template context
    return render_template('workout/measurements.html', Measurement=Measurement)

@workout.route('/measurements/<measurement_type>', methods=['GET'])
@login_required
def track_measurement(measurement_type):
    """Handle displaying measurement tracking pages."""
    valid_types = {
        'weight': {'unit': 'kg', 'min': 5, 'max': 600},
        'body_fat': {'unit': '%', 'min': 1, 'max': 50},
        'chest': {'unit': 'cm', 'min': 50, 'max': 200},
        'waist': {'unit': 'cm', 'min': 40, 'max': 200},
        'hips': {'unit': 'cm', 'min': 50, 'max': 200},
        'neck': {'unit': 'cm', 'min': 20, 'max': 100},
        'left_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'right_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'left_calf': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_calf': {'unit': 'cm', 'min': 10, 'max': 100}
    }
    
    if measurement_type not in valid_types:
        flash('Invalid measurement type')
        return redirect(url_for('workout.measurements'))
    
    # Get measurement history
    logs = Measurement.query.filter_by(
        user_id=current_user.id,
        type=measurement_type
    ).order_by(Measurement.date.desc()).all()
    
    return render_template(
        'workout/track_measurement.html',
        measurement_type=measurement_type,
        logs=logs,
        limits=valid_types[measurement_type]
    )

@workout.route('/api/weight-data')
@login_required
def get_weight_data():
    range_param = request.args.get('range', '3m')
    
    # Calculate the date range
    now = datetime.utcnow()
    if range_param == '3m':
        start_date = now - timedelta(days=90)
    elif range_param == '6m':
        start_date = now - timedelta(days=180)
    elif range_param == 'cy':
        # Get first day of current year
        start_date = datetime(now.year, 1, 1)
    else:  # all time
        start_date = datetime.min
    
    # Get weight logs for the selected period
    logs = Measurement.query.filter(
        Measurement.user_id == current_user.id,
        Measurement.type == 'weight',
        Measurement.date >= start_date
    ).order_by(Measurement.date).all()
    
    # Format data for Chart.js
    labels = [log.date.strftime('%Y-%m-%d') for log in logs]
    values = [float(log.value) for log in logs]
    
    return jsonify({
        'labels': labels,
        'values': values
    })

@workout.route('/api/measurement-data/<measurement_type>')
@login_required
def get_measurement_data(measurement_type):
    range_param = request.args.get('range', '3m')
    
    # Calculate the date range
    now = datetime.utcnow()
    if range_param == '3m':
        start_date = now - timedelta(days=90)
    elif range_param == '6m':
        start_date = now - timedelta(days=180)
    elif range_param == 'cy':
        # Get first day of current year
        start_date = datetime(now.year, 1, 1)
    else:  # all time
        start_date = datetime.min
    
    # Get logs for the selected period
    logs = Measurement.query.filter(
        Measurement.user_id == current_user.id,
        Measurement.type == measurement_type,
        Measurement.date >= start_date
    ).order_by(Measurement.date).all()
    
    # Format data for Chart.js
    labels = [log.date.strftime('%Y-%m-%d') for log in logs]
    values = [float(log.value) for log in logs]
    
    return jsonify({
        'labels': labels,
        'values': values
    })

@workout.route('/measurements/<measurement_type>', methods=['POST'])
@login_required
def log_measurement(measurement_type):
    data = request.get_json()
    value = data.get('value')
    unit = data.get('unit')
    
    valid_types = {
        'weight': {'unit': 'kg', 'min': 5, 'max': 600},
        'body_fat': {'unit': '%', 'min': 1, 'max': 50},
        'chest': {'unit': 'cm', 'min': 50, 'max': 200},
        'waist': {'unit': 'cm', 'min': 40, 'max': 200},
        'hips': {'unit': 'cm', 'min': 50, 'max': 200},
        'neck': {'unit': 'cm', 'min': 20, 'max': 100},
        'left_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_bicep': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_forearm': {'unit': 'cm', 'min': 10, 'max': 100},
        'left_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'right_thigh': {'unit': 'cm', 'min': 20, 'max': 150},
        'left_calf': {'unit': 'cm', 'min': 10, 'max': 100},
        'right_calf': {'unit': 'cm', 'min': 10, 'max': 100}
    }
    
    if measurement_type not in valid_types:
        return jsonify({'success': False, 'error': 'Invalid measurement type'}), 400
        
    # Convert value based on unit
    try:
        value = float(value)
        if unit == 'lbs':
            value = value * 0.45359237  # Convert to kg
        elif unit == 'in':
            value = value * 2.54  # Convert to cm
            
        # Validate converted value
        if value < valid_types[measurement_type]['min'] or value > valid_types[measurement_type]['max']:
            return jsonify({
                'success': False, 
                'error': f"Value must be between {valid_types[measurement_type]['min']} and {valid_types[measurement_type]['max']} {valid_types[measurement_type]['unit']}"
            }), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid value'}), 400
    
    # Create new measurement
    log = Measurement(
        user_id=current_user.id,
        type=measurement_type,
        value=value,
        unit=valid_types[measurement_type]['unit'],
        date=datetime.utcnow()
    )
    
    db.session.add(log)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@workout.route('/delete-measurement/<int:log_id>', methods=['DELETE'])
@login_required
def delete_measurement(log_id):
    """Delete a specific measurement log."""
    log = Measurement.query.get_or_404(log_id)

    if log.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    if log.type == 'weight' and Measurement.query.filter_by(user_id=current_user.id, type='weight').count() <= 1:
        return jsonify({'success': False, 'error': 'You must have at least one weight logged at all times'}), 400

    try:
        db.session.delete(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500