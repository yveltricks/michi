#!/usr/bin/env python
# Script to fix specific comment issue in workout.py

with open('app/workout.py', 'r') as f:
    lines = f.readlines()

for i in range(len(lines)):
    # Fix the issue with the broken comment at line 104-105
    if i == 104 and lines[i].strip() == '#' and i+1 < len(lines):
        # Combine the comment line and the next line
        lines[i] = '            # ' + lines[i+1].strip() + '\n'
        # Mark the next line for removal
        lines[i+1] = ''

# Remove empty lines
fixed_lines = [line for line in lines if line != '']

with open('app/workout.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed specific comment issue in app/workout.py") 