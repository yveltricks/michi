#!/usr/bin/env python
# Script to fix broken try statement in workout.py

with open('app/workout.py', 'r') as file:
    lines = file.readlines()

# Print the problematic lines for debugging
print("Line 149:", repr(lines[149]))
print("Line 150:", repr(lines[150]))
print("Line 151:", repr(lines[151]))
print("Line 152:", repr(lines[152]))

# Fix the broken try statement
if len(lines) > 152:
    # Lines 149-151 have the broken try statement
    # Replace them with a proper try statement
    lines[149] = '    try:\n'
    lines[150] = ''  # Empty line to be removed later
    lines[151] = ''  # Empty line to be removed later

# Remove empty lines
lines = [line for line in lines if line != '']

# Write the fixed content back
with open('app/workout.py', 'w') as file:
    file.writelines(lines)

print("Fixed broken try statement in app/workout.py") 