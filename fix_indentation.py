#!/usr/bin/env python
# Script to fix indentation in workout.py

with open('app/workout.py', 'r') as f:
    lines = f.readlines()

fixed_lines = []
for i, line in enumerate(lines):
    # Fix the specific issue at line 150 after the try: statement
    if i == 149 and line.strip() == "# Create new session":
        # Add proper indentation
        fixed_lines.append("        " + line.lstrip())
    else:
        fixed_lines.append(line)

with open('app/workout.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed indentation in app/workout.py") 