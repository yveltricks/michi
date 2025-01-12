# File: app/filters.py
import json

def init_filters(app):
    @app.template_filter('from_json')
    def from_json_filter(value):
        return json.loads(value) if value else []
    
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