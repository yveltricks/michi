#!/usr/bin/env python
# Script to fix indentation in workout.py

import re

with open('app/workout.py', 'r') as f:
    content = f.read()

# Check if there are any incomplete try blocks
try_pattern = re.compile(r'(\s+)try:\s*\n\s*#')

# Fix all occurrences
fixed_content = content

# Find all 'try:' statements followed by comments with incorrect indentation
matches = try_pattern.finditer(fixed_content)
for match in matches:
    indent = match.group(1)  # Original indentation before try
    # Find the position right after 'try:\n'
    pos = match.end() - 1
    
    # Get the next line with wrong indentation
    next_line_start = pos + 1
    next_line_end = fixed_content.find('\n', next_line_start)
    if next_line_end == -1:
        next_line_end = len(fixed_content)
    
    next_line = fixed_content[next_line_start:next_line_end]
    
    # Add proper indentation (4 more spaces)
    properly_indented_line = indent + '    ' + next_line.lstrip()
    
    # Replace the original line with the properly indented one
    fixed_content = fixed_content[:next_line_start] + properly_indented_line + fixed_content[next_line_end:]

with open('app/workout.py', 'w') as f:
    f.write(fixed_content)

print("Fixed indentation issues in app/workout.py") 