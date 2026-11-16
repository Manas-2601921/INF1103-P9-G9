"""Create the shared manager instances used by the application.

Manager implementations should not import this module; pass collaborators
into their constructors when needed.
"""

from data_manager import DataManager
from logic_manager import LogicManager
from IOManager import IOManager
from dashboard.input_section import InputSection
from ai_manager import AIManager


data_manager = DataManager()
logic_manager = LogicManager()
io_manager = IOManager(data_manager)
input_section = InputSection()

ai_manager = AIManager()
