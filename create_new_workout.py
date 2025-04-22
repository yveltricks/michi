#!/usr/bin/env python
# Script to fix indentation issues in workout.py

with open('app/workout.py', 'r') as file:
    content = file.read()

# Search for the log_workout function
start_marker = "@workout.route('/log-workout', methods=['POST'])"
end_marker = "@workout.route('/api/previous-values/<int:exercise_id>')"

start_index = content.find(start_marker)
end_index = content.find(end_marker, start_index)

if start_index == -1 or end_index == -1:
    print("Could not find the log_workout function!")
    exit(1)

# Extract everything before and after the function
before_function = content[:start_index]
after_function = content[end_index:]

# Replace the problematic function with a fixed version
fixed_function = """@workout.route('/log-workout', methods=['POST'])
@login_required
def log_workout():
    data = request.get_json()
    exercises_data = data.get('exercises', [])

    # Get user's latest bodyweight for volume calculations
    latest_bodyweight = Measurement.query.filter_by(user_id=current_user.id, type='weight')\\
        .order_by(Measurement.date.desc()).first()
    bodyweight = latest_bodyweight.value if latest_bodyweight else None

    try:
        # Create new session
        new_session = Session(
            user_id=current_user.id,
            session_date=datetime.utcnow(),
            duration=f"{data.get('duration', 0)} seconds",
            title=data.get('title', 'Workout'),
            description=data.get('description', ''),
            session_rating=data.get('rating', 5),
            photo=data.get('photo_url', None),
            volume=data.get('volume', 0)  # Store volume from client
        )
        
        # Try to set the new columns, but handle if they don't exist
        try:
            new_session.sets_completed = data.get('sets_completed', 0)
            new_session.total_reps = data.get('total_reps', 0)
        except Exception as column_error:
            print(f"Warning: Could not set new columns: {str(column_error)}")
            # Continue without these fields
        
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
                    set_type=set_data.get('set_type', 'normal'),
                    volume=set_volume  # Store the calculated volume
                )

                # Add all relevant fields based on exercise type
                for field in exercise.get_input_fields():
                    setattr(new_set, field, set_data.get(field, 0))

                    # Check if set is within range and set the flag
                    if exercise and exercise.range_enabled:
                        within_range = False
                        
                        if exercise.input_type.endswith('reps'):
                            if exercise.min_reps and exercise.max_reps:
                                reps = set_data.get('reps', 0)
                                within_range = exercise.min_reps <= reps <= exercise.max_reps
                        elif exercise.input_type.endswith('duration'):
                            if exercise.min_duration and exercise.max_duration:
                                time = set_data.get('time', 0)
                                within_range = exercise.min_duration <= time <= exercise.max_duration
                        elif exercise.input_type.endswith('distance'):
                            if exercise.min_distance and exercise.max_distance:
                                distance = set_data.get('distance', 0)
                                within_range = exercise.min_distance <= distance <= exercise.max_distance
                        
                        new_set.within_range = within_range

                db.session.add(new_set)

        # Update session with total volume and exercise data
        new_session.exercises = json.dumps(formatted_exercises)
            
        # If client provided volume is 0, use our calculated volume
        if new_session.volume == 0:
            new_session.volume = total_volume
        
        # Format duration properly for display
        duration_seconds = data.get('duration', 0)
        if duration_seconds:
            try:
                # Ensure duration_seconds is an integer before division
                if isinstance(duration_seconds, str):
                    duration_seconds = int(duration_seconds.strip())
                minutes = int(duration_seconds) // 60  # Use integer division
                new_session.duration = f"{minutes} minutes"
            except (ValueError, TypeError) as e:
                print(f"Error formatting duration: {str(e)}")
                new_session.duration = "0 minutes"  # Default if conversion fails
        
        # Use the EXP gained during the workout from the client
        base_exp = data.get('exp_gained', 0)
        
        # Calculate consistency bonus
        consistency_bonus = 0
        
        # Check workout frequency (last 7 days)
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        recent_workouts = Session.query.filter(
            Session.user_id == current_user.id,
            Session.session_date >= one_week_ago
        ).count()
        
        # Bonus for multiple workouts per week
        if recent_workouts >= 3:
            consistency_bonus += 20  # Bonus for 3+ workouts per week
        elif recent_workouts >= 1:
            consistency_bonus += 10  # Smaller bonus for at least 1 workout per week
        
        # Check for streaks (consecutive days)
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        yesterday_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        
        worked_out_yesterday = Session.query.filter(
            Session.user_id == current_user.id,
            Session.session_date >= yesterday_start,
            Session.session_date <= yesterday_end
        ).first() is not None
        
        # Update streak
        if worked_out_yesterday:
            # If they worked out yesterday, increment streak
            current_user.streak += 1
        else:
            # Reset streak if they didn't work out yesterday
            current_user.streak = 1
        
        # Bonus for maintaining streak
        if current_user.streak >= 7:
            consistency_bonus += 30  # Bonus for 7+ day streak
        elif current_user.streak >= 3:
            consistency_bonus += 15  # Bonus for 3+ day streak
        
        # Set total EXP gained (base + bonus)
        total_exp_gained = base_exp + consistency_bonus
        new_session.exp_gained = total_exp_gained

        # Update user's exp
        current_user.exp += total_exp_gained
        current_user.update_level()

        db.session.commit()
        return jsonify({
            'success': True,
            'session_id': new_session.id,
            'exp_gained': total_exp_gained
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error saving workout: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
"""

# Combine everything
fixed_content = before_function + fixed_function + after_function

# Write the fixed content back
with open('app/workout.py', 'w') as file:
    file.write(fixed_content)

print("Fixed broken log_workout function in app/workout.py") 