from django.urls import path

from . import views

urlpatterns = [
    path("Mantenimiento", views.Mantenimiento, name="Mantenimiento"),
    path("ObtenerListas", views.ObtenerListas, name="ObtenerListas"),
    path("ObtenerProductoPorId", views.ObtenerProductoPorId, name="ObtenerProductoPorId"),
    path("GrabarProducto", views.GrabarProducto, name="GrabarProducto"),
    path("EliminarProductoPorId", views.EliminarProductoPorId, name="EliminarProductoPorId"),
]
