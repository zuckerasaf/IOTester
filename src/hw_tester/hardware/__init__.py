"""
Hardware abstraction layer for Controllino/Arduino communication and pin management.
"""
from .pin import Pin, Connector

__all__ = ['Pin', 'Connector']
