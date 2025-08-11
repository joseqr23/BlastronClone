# utils/paths.py
import os
import sys

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, compatible con PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # Cuando corre desde el .exe empaquetado
        return os.path.join(sys._MEIPASS, relative_path)
    # Cuando corre en desarrollo
    return os.path.join(os.path.abspath("."), relative_path)
