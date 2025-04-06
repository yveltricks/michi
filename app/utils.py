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
        'total_duration': sum(int(s.duration.split()[0]) for s in this_week_sessions),  # Assumes duration is stored as "X minutes"
        'total_volume': sum(s.volume for s in this_week_sessions)
    }
    
    # Calculate last week's stats for comparison
    last_week = {
        'exp_gained': sum(s.exp_gained for s in last_week_sessions),
        'workout_count': len(last_week_sessions),
        'total_duration': sum(int(s.duration.split()[0]) for s in last_week_sessions),
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