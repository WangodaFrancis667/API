# Later after API testing, change the authentication classes to IsAuthenticated

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.utils import timezone

from .serializers import (
    NotificationSerializer, CreateCustomNotificationSerializer,
    MarkReadSerializer, PhoneQuerySerializer, 
)


# from .services import get_user_notifications, get_unread_count, mark_as_read, mark_all_as_read
# from .services import delete_notification, delete_all_for_user, get_notifications_by_phone
# from .services import create_custom_notification



from .services import (
    get_user_notifications, get_unread_count, mark_as_read, mark_all_as_read,
    delete_notification, delete_all_for_user, get_notifications_by_phone,
    create_custom_notification, create_order_update_notification
)

from .models import UserTypes

User = get_user_model()


class ListNotificationsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get(self, request):
        user = request.user

        # determine user_type from your user model (adjust to your reality)
        user_type = getattr(user, 'role', '').lower() or UserTypes.BUYER
        unread = request.query_params.get('unread_only', '0') == '1'
        limit = int(request.query_params.get('limit', '50'))

        data, from_cache = get_user_notifications(
            user=user, user_type=user_type, unread_only=unread, limit=limit, exclude_otp=True
        )
        return Response({"cache": from_cache, "results": data})
    

class UnreadCountView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_type = getattr(user, 'role', '').lower() or UserTypes.BUYER
        count, from_cache = get_unread_count(user=user, user_type=user_type, exclude_otp=True)
        return Response({"cache": from_cache, "count": count})


class MarkAsReadView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MarkReadSerializer

    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        updated = mark_as_read(s.validated_data['notification_id'], user=request.user)
        return Response({"updated": updated})

class MarkAllAsReadView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user_type = getattr(user, 'role', '').lower() or UserTypes.BUYER
        mark_all_as_read(user=user, user_type=user_type)
        return Response({"detail": "All notifications marked as read."})

class DeleteNotificationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MarkReadSerializer  # reuse to accept id

    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        deleted = delete_notification(s.validated_data['notification_id'], user=request.user)
        return Response({"deleted": deleted})

class DeleteAllForUserView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user_type = getattr(user, 'role', '').lower() or UserTypes.BUYER
        delete_all_for_user(user=user, user_type=user_type)
        return Response({"detail": "All notifications deleted."})

class PhoneNotificationsView(generics.GenericAPIView):
    permission_classes = [AllowAny]  
    serializer_class = PhoneQuerySerializer

    def get(self, request):
        s = self.get_serializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        results = get_notifications_by_phone(
            phone=s.validated_data['phone'],
            unread_only=s.validated_data['unread_only'],
            limit=s.validated_data['limit']
        )
        return Response({"results": results})

class CreateCustomNotificationView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = CreateCustomNotificationSerializer

    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            user = User.objects.get(id=s.validated_data['user_id'])
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        n = create_custom_notification(
            user=user,
            user_type=s.validated_data['user_type'],
            title=s.validated_data['title'],
            message=s.validated_data['message'],
            phone=s.validated_data.get('phone') or "",
            is_urgent=s.validated_data['is_urgent'],
            expires_at=timezone.now() + timezone.timedelta(
                minutes=s.validated_data.get('expires_minutes', 0)
            ) if s.validated_data.get('expires_minutes') else None,
            ntype=s.validated_data['type'],
        )
        if n is None:
            return Response({"detail": "Blocked by vendor notification restriction."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(NotificationSerializer(n).data, status=status.HTTP_201_CREATED)

