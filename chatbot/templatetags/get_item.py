# Custom template filter to allow dictionary key access in Django templates
from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key) 