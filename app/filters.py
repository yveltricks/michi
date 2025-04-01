# File: app/filters.py
import json

def init_filters(app):
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
                if not isinstance(result, (list, dict)):
                    print(f"Warning: JSON parsed to non-iterable type: {type(result)}")
                    return []
                return result
            # If it's already an object (dict, list, etc.), return it unchanged
            elif isinstance(value, (list, dict)):
                return value
            # If it's an SQLAlchemy model or another object, try to convert to dict if possible
            elif hasattr(value, '__iter__') and not isinstance(value, str):
                # It's an iterable object, return it
                return value
            else:
                # Non-iterable type that can't be used in templates safely
                print(f"Warning: from_json received non-iterable type: {type(value)}")
                return []
        except (json.JSONDecodeError, TypeError) as e:
            # Log the error for debugging
            print(f"Error parsing JSON ({type(e).__name__}): {value}")
            return []
    
    @app.template_filter('format_duration')
    def format_duration_filter(duration):
        """Convert duration to a human-readable format"""
        if not duration:
            return "0 min"
        
        try:
            # Handle cases where duration is like "112 minutes" or just "112"
            if isinstance(duration, str):
                duration = duration.lower().strip()
                if "minute" in duration:
                    minutes = int(duration.split()[0])
                else:
                    minutes = int(duration)
            else:
                minutes = int(duration)
                
            hours = minutes // 60
            remaining_minutes = minutes % 60
            
            if hours > 0:
                return f"{hours}h {remaining_minutes}min"
            return f"{remaining_minutes}min"
        except (ValueError, TypeError):
            return duration  # Return original value if conversion fails