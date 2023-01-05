from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('form', views.form, name='form'),
    path('search', views.search, name='search'),
    path('download_id', views.download_id, name='download_id'),
    path('about', views.about, name='about')
]
