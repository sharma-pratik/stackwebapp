from rest_framework.views import APIView

class PerMinThrottle(APIView):
    """
    Throttle class for per minutes
    """
    throttle_scope = "per_min"

class PerHourThrottle(APIView):
    """
    Throttle class for per hour
    """
    throttle_scope = "per_hour"

