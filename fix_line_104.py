#!/usr/bin/env python
# Script to fix line 104 in workout.py

with open('app/workout.py', 'r') as file:
    lines = file.readlines()

# Print the problematic lines for debugging
print("Line 103:", repr(lines[103]))
print("Line 104:", repr(lines[104]))
print("Line 105:", repr(lines[105]))
print("Line 106:", repr(lines[106]))

# Fix line 104-105 by replacing them with a proper comment
if len(lines) > 105:
    # Remove line 104 (the # only line)
    del lines[104]
    # Fix line 105 (now 104 after deletion) to be a proper comment
    if len(lines) > 104:
        lines[104] = '            # Get the index in recent exercises (lower is more recent)\n'

# Write the fixed content back
with open('app/workout.py', 'w') as file:
    file.writelines(lines)

print("Fixed line 104 in app/workout.py") 