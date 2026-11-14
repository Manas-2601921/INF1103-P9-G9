"""Create the shared manager instances used by the application.

Keep construction here and orchestration in main.py. As other managers become
classes, their instances can be added here. Manager implementations should not
import this module; pass collaborators into their constructors when needed.
"""

from data_manager import DataManager
from logic_manager import LogicManager
from IOManager import IOManager
from dashboard.input_section import InputSection


data_manager = DataManager()
logic_manager = LogicManager()
io_manager = IOManager(data_manager)
input_section = InputSection()

