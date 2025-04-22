from datetime import datetime, timedelta
from . import db
from .models import Session

def get_weekly_stats(user_id):
    """
    # I'll use this function to calculate a user's weekly statistics
    # It returns things like exp gained, number of workouts, etc.
    """
    # Get the start of the current week (Monday)
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get the start of last week
    start_of_last_week = start_of_week - timedelta(days=7)
    
    # Get this week's sessions
    this_week_sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.session_date >= start_of_week
    ).all()
    
    # Get last week's sessions
    last_week_sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.session_date >= start_of_last_week,
        Session.session_date < start_of_week
    ).all()
    
    # Calculate this week's stats
    this_week = {
        'exp_gained': sum(s.exp_gained for s in this_week_sessions),
        'workout_count': len(this_week_sessions),
        'total_duration': sum(parse_duration(s.duration) for s in this_week_sessions),  # Handle "X minutes" format safely
        'total_volume': sum(s.volume for s in this_week_sessions)
    }
    
    # Calculate last week's stats for comparison
    last_week = {
        'exp_gained': sum(s.exp_gained for s in last_week_sessions),
        'workout_count': len(last_week_sessions),
        'total_duration': sum(parse_duration(s.duration) for s in last_week_sessions),
        'total_volume': sum(s.volume for s in last_week_sessions)
    }
    
    # Calculate trends (better or worse than last week)
    trends = {
        'exp_gained': this_week['exp_gained'] >= last_week['exp_gained'],
        'workout_count': this_week['workout_count'] >= last_week['workout_count'],
        'total_duration': this_week['total_duration'] >= last_week['total_duration'],
        'total_volume': this_week['total_volume'] >= last_week['total_volume']
    }
    
    return this_week, trends

def calculate_streak(user_id):
    """
    # This function calculates the user's weekly streak
    # A streak continues if they do at least one workout per week
    """
    today = datetime.utcnow()
    current_week_start = today - timedelta(days=today.weekday())
    streak = 0
    
    while True:
        week_start = current_week_start - timedelta(weeks=streak)
        week_end = week_start + timedelta(days=7)
        
        # Check if user had any sessions this week
        sessions = Session.query.filter(
            Session.user_id == user_id,
            Session.session_date >= week_start,
            Session.session_date < week_end
        ).first()
        
        if not sessions:
            break
            
        streak += 1
    
    return streak

def calculate_weekly_stats(user_id):
    """Calculate stats for the current week"""
    from app.models import Workout, User, Session
    from sqlalchemy import func
    
    # Calculate current week boundaries
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)
    
    # Calculate previous week boundaries
    start_of_prev_week = start_of_week - timedelta(days=7)
    end_of_prev_week = start_of_week
    
    # Statistics for current week
    current_week_workouts = Workout.query.filter(
        Workout.user_id == user_id,
        Workout.date >= start_of_week,
        Workout.date < end_of_week,
        Workout.completed == True
    ).all()
    
    # Debug output
    print(f"Found {len(current_week_workouts)} workouts for this week")
    for w in current_week_workouts:
        print(f"Workout {w.id}: exp_gained={w.exp_gained}, volume={w.volume}, duration={w.duration}")
    
    # Use both Workout and Session data for EXP (in case one has missing data)
    current_week_sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.session_date >= start_of_week,
        Session.session_date < end_of_week
    ).all()
    
    # Calculate total EXP from both workouts and sessions
    total_exp = 0
    # First try workouts
    workout_exp = sum(w.exp_gained or 0 for w in current_week_workouts)
    # If no exp from workouts, try sessions
    if workout_exp == 0:
        total_exp = sum(s.exp_gained or 0 for s in current_week_sessions)
    else:
        total_exp = workout_exp
    
    current_week_stats = {
        'workout_count': len(current_week_workouts),
        'total_volume': sum(w.volume or 0 for w in current_week_workouts),
        'total_duration': sum(parse_duration(w.duration) for w in current_week_workouts),
        'total_exp': total_exp
    }
    
    # Statistics for previous week
    prev_week_workouts = Workout.query.filter(
        Workout.user_id == user_id,
        Workout.date >= start_of_prev_week,
        Workout.date < end_of_prev_week,
        Workout.completed == True
    ).all()
    
    # Use both Workout and Session data for EXP (in case one has missing data)
    prev_week_sessions = Session.query.filter(
        Session.user_id == user_id,
        Session.session_date >= start_of_prev_week,
        Session.session_date < end_of_prev_week
    ).all()
    
    # Calculate total EXP from both workouts and sessions for previous week
    prev_total_exp = 0
    prev_workout_exp = sum(w.exp_gained or 0 for w in prev_week_workouts)
    if prev_workout_exp == 0:
        prev_total_exp = sum(s.exp_gained or 0 for s in prev_week_sessions)
    else:
        prev_total_exp = prev_workout_exp
    
    prev_week_stats = {
        'workout_count': len(prev_week_workouts),
        'total_volume': sum(w.volume or 0 for w in prev_week_workouts),
        'total_duration': sum(parse_duration(w.duration) for w in prev_week_workouts),
        'total_exp': prev_total_exp
    }
    
    # Print debug info
    print(f"Current week stats: {current_week_stats}")
    print(f"Previous week stats: {prev_week_stats}")
    
    # Calculate change indicators (1 = better, 0 = same, -1 = worse)
    comparisons = {
        'workout_count': compare_values(current_week_stats['workout_count'], prev_week_stats['workout_count']),
        'total_volume': compare_values(current_week_stats['total_volume'], prev_week_stats['total_volume']),
        'total_duration': compare_values(current_week_stats['total_duration'], prev_week_stats['total_duration']),
        'total_exp': compare_values(current_week_stats['total_exp'], prev_week_stats['total_exp'])
    }
    
    # Get user's current streak
    user = User.query.get(user_id)
    streak = user.streak if user else 0
    
    # Get user's current level
    level = user.level if user else 1
    
    return {
        'current_week': current_week_stats,
        'prev_week': prev_week_stats,
        'comparisons': comparisons,
        'streak': streak,
        'level': level
    }

def compare_values(current, previous):
    """Compare two values and return 1 (better), 0 (same), or -1 (worse)"""
    if current > previous:
        return 1
    elif current < previous:
        return -1
    else:
        return 0

def compare_exercise_progress(workout_id, user_id):
    """
    Compare exercise performance in a workout with previous performances
    Returns dictionary with exercise_id keys and comparison values (1, 0, -1)
    """
    from app.models import Workout, WorkoutExercise, WorkoutSet
    
    exercise_comparisons = {}
    
    # Get the workout
    workout = Workout.query.get(workout_id)
    if not workout or workout.user_id != user_id:
        return {}
    
    # Process each exercise in the workout
    for workout_exercise in workout.exercises:
        exercise_id = workout_exercise.exercise_id
        
        # Get previous workout with this exercise
        prev_workout_exercise = WorkoutExercise.query.join(Workout).filter(
            WorkoutExercise.exercise_id == exercise_id,
            Workout.user_id == user_id,
            Workout.id != workout_id,
            Workout.completed == True
        ).order_by(Workout.date.desc()).first()
        
        if not prev_workout_exercise:
            # No previous workout with this exercise, so it's an improvement
            exercise_comparisons[exercise_id] = 1
            continue
        
        # Calculate volume for current exercise
        current_volume = sum(
            s.weight * s.reps if s.weight and s.reps else 0 
            for s in workout_exercise.sets if s.completed
        )
        
        # Calculate volume for previous exercise
        prev_volume = sum(
            s.weight * s.reps if s.weight and s.reps else 0 
            for s in prev_workout_exercise.sets if s.completed
        )
        
        # Compare volumes
        exercise_comparisons[exercise_id] = compare_values(current_volume, prev_volume)
    
    return exercise_comparisons

"""Utility functions for the application"""

# Unit conversion constants and functions
KG_TO_LBS = 2.20462  # 1 kg = 2.20462 lbs
LBS_TO_KG = 0.453592  # 1 lbs = 0.453592 kg
KM_TO_MI = 0.621371  # 1 km = 0.621371 miles
MI_TO_KM = 1.60934  # 1 mile = 1.60934 km
CM_TO_IN = 0.393701  # 1 cm = 0.393701 inches
IN_TO_CM = 2.54  # 1 inch = 2.54 cm

def convert_weight(value, from_unit, to_unit):
    """Convert weight between kg and lbs"""
    if from_unit == to_unit:
        return value
    
    if from_unit == 'kg' and to_unit == 'lbs':
        return value * KG_TO_LBS
    elif from_unit == 'lbs' and to_unit == 'kg':
        return value * LBS_TO_KG
    
    raise ValueError(f"Unsupported weight unit conversion: {from_unit} to {to_unit}")

def convert_distance(value, from_unit, to_unit):
    """Convert distance between km and miles"""
    if from_unit == to_unit:
        return value
    
    if from_unit == 'km' and to_unit == 'mi':
        return value * KM_TO_MI
    elif from_unit == 'mi' and to_unit == 'km':
        return value * MI_TO_KM
    
    raise ValueError(f"Unsupported distance unit conversion: {from_unit} to {to_unit}")

def convert_measurement(value, from_unit, to_unit):
    """Convert body measurements between cm and inches"""
    if from_unit == to_unit:
        return value
    
    if from_unit == 'cm' and to_unit == 'in':
        return value * CM_TO_IN
    elif from_unit == 'in' and to_unit == 'cm':
        return value * IN_TO_CM
    
    raise ValueError(f"Unsupported measurement unit conversion: {from_unit} to {to_unit}")

def get_weight_unit_label(user):
    """Get the weight unit label based on user preferences"""
    return 'lbs' if user.preferred_weight_unit == 'lbs' else 'kg'

def get_distance_unit_label(user):
    """Get the distance unit label based on user preferences"""
    return 'mi' if user.preferred_distance_unit == 'mi' else 'km'

def get_measurement_unit_label(user):
    """Get the measurement unit label based on user preferences"""
    return 'in' if user.preferred_measurement_unit == 'in' else 'cm'

def format_weight_for_display(weight_kg, user):
    """Format weight for display based on user preferences"""
    if user.preferred_weight_unit == 'lbs':
        return f"{convert_weight(weight_kg, 'kg', 'lbs'):.1f} lbs"
    return f"{weight_kg:.1f} kg"

def format_distance_for_display(distance_km, user):
    """Format distance for display based on user preferences"""
    if user.preferred_distance_unit == 'mi':
        return f"{convert_distance(distance_km, 'km', 'mi'):.2f} mi"
    return f"{distance_km:.2f} km"

def format_measurement_for_display(measurement_cm, user):
    """Format measurement for display based on user preferences"""
    if user.preferred_measurement_unit == 'in':
        return f"{convert_measurement(measurement_cm, 'cm', 'in'):.1f} in"
    return f"{measurement_cm:.1f} cm"

def normalize_weight_to_kg(weight, unit):
    """Convert weight to kg regardless of input unit"""
    if unit == 'lbs':
        return weight * LBS_TO_KG
    return weight  # Assume kg

def convert_volume_to_preferred_unit(volume_in_kg, preferred_unit):
    """Convert volume from kg to user's preferred unit for display"""
    if preferred_unit == 'lbs':
        return round(volume_in_kg * KG_TO_LBS, 2)
    return round(volume_in_kg, 2)  # Already in kg, but round for consistency

def normalize_distance_to_km(distance, unit):
    """Convert distance to km regardless of input unit"""
    if unit == 'mi':
        return distance * MI_TO_KM
    return distance  # Assume km

def normalize_measurement_to_cm(measurement, unit):
    """Convert measurement to cm regardless of input unit"""
    if unit == 'in':
        return measurement * IN_TO_CM
    return measurement  # Assume cm

def parse_duration(duration_str):
    """
    Safely parse a duration value into seconds.
    
    Handles:
    - Integers/floats (assumed to be in seconds)
    - Strings like "10 minutes", "1h 30m", "90 seconds"
    - None values
    - String representations of numbers
    - Complex string formats with both hours and minutes
    
    Returns integer seconds
    """
    try:
        # If None or empty, return 0
        if duration_str is None or duration_str == '':
            return 0
            
        # If it's already a number, convert and return it
        if isinstance(duration_str, (int, float)):
            return int(duration_str)
        
        # Handle string values
        duration_str = str(duration_str).strip().lower()
        
        # If it's just a number as string, convert directly
        if duration_str.isdigit():
            return int(duration_str)
            
        # Check for hours/minutes/seconds format
        import re
        
        # Try to find hours, minutes, and seconds in the string
        hours_match = re.search(r'(\d+)\s*(?:h|hour|hours)', duration_str)
        minutes_match = re.search(r'(\d+)\s*(?:m|min|minute|minutes)', duration_str)
        seconds_match = re.search(r'(\d+)\s*(?:s|sec|second|seconds)', duration_str)
        
        total_seconds = 0
        
        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600
            
        if minutes_match:
            total_seconds += int(minutes_match.group(1)) * 60
            
        if seconds_match:
            total_seconds += int(seconds_match.group(1))
            
        # If we found any time units, return the total
        if hours_match or minutes_match or seconds_match:
            return total_seconds
            
        # Fallback: just extract any number and assume it's minutes
        match = re.search(r'(\d+)', duration_str)
        if match:
            # Assume it's minutes if no unit specified
            return int(match.group(1)) * 60
        
        # If all else fails, return 0
        return 0
    except Exception as e:
        print(f"Error parsing duration '{duration_str}': {str(e)}")
        return 0