# attendance/templatetags/custom_filters.py
from django import template
import json


register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def jsonify(value):
    """Converts a Django model or QuerySet to a JSON serializable format."""
    if isinstance(value, (list, tuple)):
        # If value is a list or tuple, convert each item to a dictionary (if it's a model object).
        value = [obj_to_dict(v) if hasattr(v, '__dict__') else v for v in value]
    elif hasattr(value, '__dict__'):
        # If value is a model object, convert it to a dictionary.
        value = obj_to_dict(value)
    
    return json.dumps(value)


def obj_to_dict(obj):
    """Convert a Django model instance to a dictionary."""
    if hasattr(obj, '__dict__'):
        # Get the model fields, excluding private attributes.
        return {field: getattr(obj, field) for field in obj.__dict__ if not field.startswith('_')}
    return {}