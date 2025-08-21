from celery import shared_task
from notifications.services import notify_buyer_status
from notifications.services import _create as create_notification


@shared_task
def send_order_email(order_id: int):
    # implement if you want a confirmation email
    pass


@shared_task
def notify_buyer_on_status_change(*, buyer_id: int, order_id: int, status: str, product_name: str):
    notify_buyer_status.delay(
        buyer_id=buyer_id,
        order_id=order_id,
        status=status,
        product_name=product_name
    )


@shared_task
def notify_admin_return_request(*, order_id: int, return_id: int, buyer_id: int):
    title = "Return Requested"
    msg = f"Return requested for Order #{order_id}. Return ID: {return_id}"
    # Assuming we notify admins (user_type=general)
    # If admins have a known id/notification endpoint, adapt as needed
    create_notification(
        user_id=1,  # admin
        user_type="general",
        phone="admin",  # placeholder
        type_="general",
        title=title,
        message=msg,
        is_urgent=True
    )
