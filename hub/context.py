from django.conf import settings


def site(request):
    return {"SITE_NAME": "ElectroLab", "AI_LIVE": settings.AI_ENABLED}
