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