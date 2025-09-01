from datetime import datetime, timedelta
from django.utils.timezone import make_aware


def get_date_range(period: str):
    now = datetime.now()
    end_date = make_aware(datetime.combine(now.date(), datetime.max.time()))

    if period == "today":
        start_date = make_aware(datetime.combine(now.date(), datetime.min.time()))
    elif period == "this_week":
        start_date = make_aware(datetime.combine((now - timedelta(days=now.weekday())).date(), datetime.min.time()))
    elif period == "this_month":
        start_date = make_aware(datetime.combine(now.replace(day=1).date(), datetime.min.time()))
    elif period == "last_month":
        first_day_last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day_last_month = now.replace(day=1) - timedelta(days=1)
        start_date = make_aware(datetime.combine(first_day_last_month.date(), datetime.min.time()))
        end_date = make_aware(datetime.combine(last_day_last_month.date(), datetime.max.time()))
    elif period == "last_3_months":
        start_date = make_aware(datetime.combine((now.replace(day=1) - timedelta(days=60)).date(), datetime.min.time()))
    elif period == "this_year":
        start_date = make_aware(datetime.combine(datetime(now.year, 1, 1).date(), datetime.min.time()))
    else:
        start_date = make_aware(datetime(1970, 1, 1))

    return start_date, end_date
