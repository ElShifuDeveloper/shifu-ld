from django.urls import path

from . import views_transferencia as views

urlpatterns = [
    path("CargaArchivos", views.PantallaCarga, name="PantallaCarga"),   # ajusta la ruta; la plantilla recibe SizeLote y SizeBloque
    path("ConsultaCarpetas", views.PantallaConsulta, name="PantallaConsulta"),   # galería; también recibe SizeLote y SizeBloque
    path("CrearCarpeta", views.CrearCarpeta, name="CrearCarpeta"),
    path("GrabarBloque", views.GrabarBloque, name="GrabarBloque"),
    path("GrabarLote", views.GrabarLote, name="GrabarLote"),
    path("ListarCarpetas", views.ListarCarpetas, name="ListarCarpetas"),
    path("ListarArchivos", views.ListarArchivos, name="ListarArchivos"),
    path("ListarCodigosSize", views.ListarCodigosSize, name="ListarCodigosSize"),
    path("ObtenerPaquete", views.ObtenerPaquete, name="ObtenerPaquete"),
    path("ObtenerBloque", views.ObtenerBloque, name="ObtenerBloque"),
    path("ObtenerArchivo", views.ObtenerArchivo, name="ObtenerArchivo"),
]
