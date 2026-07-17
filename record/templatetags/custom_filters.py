from django import template

register = template.Library()

@register.filter
def max_value(iterable):
    if iterable:
        return max(iterable)
    return None

@register.filter
def min_value(iterable):
    if iterable:
        return min(iterable)
    return None

@register.filter
def average(iterable):
    if iterable:
        return sum(iterable) / len(iterable)
    return None

@register.filter
def filter_failed(queryset, total_score):
    half = total_score / 2
    return [sr for sr in queryset if sr.score < half]

@register.filter
def filter_below_avg(queryset, total_score):
    if not queryset:
        return []
    scores = [sr.score for sr in queryset]
    avg = sum(scores) / len(scores)
    return [sr for sr in queryset if sr.score < avg]

@register.filter
def filter_scores(queryset, bucket):
    # bucket like "0,25" meaning scores between 0 and 25% of total
    # you can implement as needed
    pass