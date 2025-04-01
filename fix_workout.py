#!/usr/bin/env python
# Script to fix duplicate explore_routines function

with open('app/workout.py', 'r') as f:
    lines = f.readlines()

# Track duplicate functions
explore_routes_found = 0
output_lines = []

# Process each line
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this line starts a explore_routines function
    if '@workout.route(\'/explore\')' in line:
        explore_routes_found += 1
        
        # If this is the second occurrence, skip it and its body
        if explore_routes_found > 1:
            # Skip function decorator, def line, docstring, and body (about 8 lines)
            j = i
            found_closing = False
            while j < len(lines) and not found_closing:
                if 'muscle_groups=MUSCLE_GROUPS)' in lines[j]:
                    found_closing = True
                j += 1
            
            # Skip to after the function
            if found_closing:
                i = j
                continue
    
    # Add line to output
    output_lines.append(line)
    i += 1

# Write fixed file
with open('app/workout_fixed.py', 'w') as f:
    f.writelines(output_lines)

print(f"Fixed file written to app/workout_fixed.py (removed {explore_routes_found-1} duplicate functions)") 