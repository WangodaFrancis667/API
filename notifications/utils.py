from django.core.cache import cache

CACHE_TTL = 60 * 5  # 5 minutes
LIST_CACHE_KEY = "notifications:list:{uid}:{utype}:{unread}:{limit}"
COUNT_CACHE_KEY = "notifications:unread_count:{uid}:{utype}"

def invalidate_user_cache(user_id: int, user_type: str):
    """Utility function to invalidate user cache - no dependencies."""
    cache.delete(COUNT_CACHE_KEY.format(uid=user_id, utype=user_type))
    for unread in (0, 1):
        for limit in (10, 20, 50, 100):
            cache.delete(LIST_CACHE_KEY.format(uid=user_id, utype=user_type, unread=unread, limit=limit))