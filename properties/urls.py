from django.urls import path
 
from . import views
 
app_name = "properties"
 
urlpatterns = [
        # Landing page
    path("home/", views.home, name="home"),
    # Tenant side
    path("", views.house_list, name="house_list"),  # search + filters
    path("houses/<int:pk>/", views.house_detail, name="house_detail"),
 
    # Landlord side
    path("my-houses/", views.my_houses, name="my_houses"),
    path("houses/add/", views.house_create, name="house_create"),
    path("houses/<int:pk>/edit/", views.house_update, name="house_update"),
    path("houses/<int:pk>/delete/", views.house_delete, name="house_delete"),
    path("houses/<int:pk>/status/", views.toggle_status, name="toggle_status"),
    path("houses/<int:pk>/images/add/", views.image_upload, name="image_upload"),
    path("images/<int:pk>/delete/", views.image_delete, name="image_delete"),
]