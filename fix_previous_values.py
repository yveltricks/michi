#!/usr/bin/env python
# Script to fix indentation in the second previous-values function in workout.py

with open('app/workout.py', 'r') as file:
    content = file.read()

# Search for the function
start_marker = "@workout.route('/api/previous-values/<int:exercise_id>/<int:set_number>')"
end_marker = "@workout.route('/view-session/<int:session_id>')"

start_index = content.find(start_marker)
end_index = content.find(end_marker, start_index)

if start_index == -1 or end_index == -1:
    print("Could not find the function!")
    exit(1)

# Extract everything before and after the function
before_function = content[:start_index]
after_function = content[end_index:]

# Replace the problematic function with a fixed version
fixed_function = """@workout.route('/api/previous-values/<int:exercise_id>/<int:set_number>')
@login_required
def get_previous_values_at_position(exercise_id, set_number):
    """Get previous set values for a specific position"""
    try:
        print(f"Getting previous values for exercise ID: {exercise_id} at position {set_number}")
        
        # Get the most recent set for this exercise at this position
        previous_set = db.session.query(Set)\\
            .join(Session, Set.session_id == Session.id)\\
            .filter(
                Set.exercise_id == exercise_id,
                Session.user_id == current_user.id,
                Set.completed == True,
                Set.order == set_number
            )\\
            .order_by(Session.session_date.desc())\\
            .first()
        
        if not previous_set:
            print(f"No previous set found at position {set_number}")
            
            # Try to find the last set in case order doesn't match
            any_previous_set = db.session.query(Set)\\
                .join(Session, Set.session_id == Session.id)\\
                .filter(
                    Set.exercise_id == exercise_id,
                    Session.user_id == current_user.id,
                    Set.completed == True
                )\\
                .order_by(Session.session_date.desc())\\
                .first()
                
            if any_previous_set:
                print(f"Found a previous set (not at the same position)")
                return jsonify({
                    'success': True,
                    'has_previous': True,
                    'weight': any_previous_set.weight,
                    'reps': any_previous_set.reps,
                    'time': any_previous_set.time,
                    'distance': any_previous_set.distance,
                    'additional_weight': getattr(any_previous_set, 'additional_weight', None),
                    'assistance_weight': getattr(any_previous_set, 'assistance_weight', None),
                    'set_type': any_previous_set.set_type,
                    'is_exact_position': False
                })
            else:
                print(f"No previous sets found at all for exercise {exercise_id}")
                return jsonify({
                    'success': True,
                    'has_previous': False
                })
        
        print(f"Found previous set at position {set_number}: {previous_set.id}")
        
        # Get unit preferences for display
        weight_unit = current_user.preferred_weight_unit
        distance_unit = current_user.preferred_distance_unit
        
        # Import conversion utilities
        from .utils import convert_weight, convert_distance
        
        # Create response with all fields
        response = {
            'success': True,
            'has_previous': True,
            'weight': previous_set.weight,
            'reps': previous_set.reps,
            'time': previous_set.time,
            'distance': previous_set.distance,
            'order': previous_set.order,
            'set_type': previous_set.set_type,
            'is_exact_position': True
        }
        
        # Add exercise-specific fields if they exist
        if hasattr(previous_set, 'additional_weight'):
            response['additional_weight'] = previous_set.additional_weight
        
        if hasattr(previous_set, 'assistance_weight'):
            response['assistance_weight'] = previous_set.assistance_weight
        
        # Convert units if needed
        if weight_unit == 'lbs':
            if response.get('weight'):
                response['weight'] = round(convert_weight(response['weight'], 'kg', 'lbs'), 2)
            if response.get('additional_weight'):
                response['additional_weight'] = round(convert_weight(response['additional_weight'], 'kg', 'lbs'), 2)
            if response.get('assistance_weight'):
                response['assistance_weight'] = round(convert_weight(response['assistance_weight'], 'kg', 'lbs'), 2)
        
        if distance_unit == 'mi' and response.get('distance'):
            response['distance'] = round(convert_distance(response['distance'], 'km', 'mi'), 2)
        
        return jsonify(response)
    except Exception as e:
        print(f"Error getting previous values: {str(e)}")
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

print("Fixed function in app/workout.py") 