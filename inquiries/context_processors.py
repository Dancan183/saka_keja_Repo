from .models import Inquiry


def unread_inquiries(request):
    user = request.user
    if user.is_authenticated and user.is_landlord:
        count = Inquiry.objects.filter(house__landlord=user, is_read=False).count()
        return {"unread_inquiries": count}
    return {}