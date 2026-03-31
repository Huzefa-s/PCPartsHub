from django import template

register = template.Library()

@register.filter
def startswith(text, prefix):
    return text.startswith(prefix)

@register.filter
def endswith(text, suffix):
    return text.endswith(suffix)

@register.filter
def contains(text, substring):
    return substring in text
