"""Create the shared manager instances used by the application.

Keep construction here and orchestration in main.py. As other managers become
classes, their instances can be added here. Manager implementations should not
import this module; pass collaborators into their constructors when needed.

This is a shared application instance, not an enforced singleton: tests and
other applications can still create DataManager instances with separate paths.
"""

from data_manager import DataManager


data_manager = DataManager()
