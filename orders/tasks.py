from celery import shared_task

@shared_task
def send_order_email(order_id: int):
    # implement if you want a confirmation email
    pass
