#!/usr/bin/env python
# Script to fix specific indentation issues in workout.py

with open('app/workout.py', 'r') as file:
    lines = file.readlines()

# Fix the indentation at line 739
if len(lines) > 739:
    # Add proper indentation to 'exercise = ' line
    lines[738] = '        exercise = Exercise.query.get_or_404(exercise_id)\n'

# Write the fixed content back
with open('app/workout.py', 'w') as file:
    file.writelines(lines)

print("Fixed indentation issue at line 739") 