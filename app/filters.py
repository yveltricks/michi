# File: app/filters.py
# This module contains custom Jinja template filters for data formatting
# Jinja filters transform data right in the templates - very handy for formatting
import json

def init_filters(app):
    """
    Initialize custom template filters for the Flask app.
    Some filters are defined both here and in __init__.py for flexibility.
    """
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Safely convert a JSON string to a Python object.
        Returns an empty list if conversion fails."""
        if not value:
            return []
        
        try:
            if isinstance(value, str):
                result = json.loads(value)
                # Ensure the result is iterable for template safety
                # This prevents errors when templates try to loop over non-iterable values
                if not isinstance(result, (list, dict)):
                    print(f"Warning: JSON parsed to non-iterable type: {type(result)}")
                    return []
                return result
            # If it's already an object (dict, list, etc.), return it unchanged
            # This lets us use the filter consistently without worrying about input type
            elif isinstance(value, (list, dict)):
                return value
            # If it's an SQLAlchemy model or another object, try to convert to dict if possible
            # Some DB models have __iter__ methods that make them usable in templates
            elif hasattr(value, '__iter__') and not isinstance(value, str):
                # It's an iterable object, return it
                return value
            else:
                # Non-iterable type that can't be used in templates safely
                # Better to return an empty list than cause template errors
                print(f"Warning: from_json received non-iterable type: {type(value)}")
                return []
        except (json.JSONDecodeError, TypeError) as e:
            # Log the error for debugging
            # This helps us catch malformed JSON without breaking the template
            print(f"Error parsing JSON ({type(e).__name__}): {value}")
            return []
    
    @app.template_filter('format_duration')
    def format_duration_filter(duration):
        """Convert duration to a human-readable format like '30min' or '1h 15min'"""
        if not duration:
            return "0 min"
        
        try:
            # Handle cases where duration is like "112 minutes" or just "112"
            # This flexibility lets us handle different input formats from various sources
            if isinstance(duration, str):
                duration = duration.lower().strip()
                if "minute" in duration:
                    minutes = int(duration.split()[0])
                else:
                    minutes = int(duration)
            else:
                minutes = int(duration)
                
            # Convert to hours and minutes for better readability
            hours = minutes // 60
            remaining_minutes = minutes % 60
            
            # Format differently based on whether hours are present
            if hours > 0:
                return f"{hours}h {remaining_minutes}min"
            return f"{remaining_minutes}min"
        except (ValueError, TypeError):
            # If we can't parse it, just return the original
            # This is a safety net so templates don't break
            return duration  # Return original value if conversion fails