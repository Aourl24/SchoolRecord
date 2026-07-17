from django import template

register = template.Library()

@register.filter
def filter_failed(queryset, half):
    """Return student records with score < half."""
    return [sr for sr in queryset if sr.score < half]

@register.filter
def filter_below_avg(queryset, avg):
    """Return student records with score < avg."""
    return [sr for sr in queryset if sr.score < avg]

@register.filter
def split(value, arg):
    """Split a string by delimiter."""
    return value.split(arg)

@register.filter
def filter_by_bucket(score_list, bucket_str):
    """Filter scores by percentage bucket (e.g., '25' -> scores <= 25% of total)."""
    # This is a simplified version; you might need the total score.
    # For a proper implementation, you'd need record.total_score in context.
    # Here's a placeholder that returns count of scores below the bucket percentage.
    # You can adjust as needed.
    try:
        bucket = int(bucket_str)
    except ValueError:
        return 0
    # Since we don't have total_score here, we'll just return a dummy.
    # For a real implementation, pass total_score or compute in view.
    return len([s for s in score_list if s <= bucket])