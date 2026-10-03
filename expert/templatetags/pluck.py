from django import template
register = template.Library()

@register.filter
def pluck(list_obj, key):
    return [item[key] for item in list_obj]
