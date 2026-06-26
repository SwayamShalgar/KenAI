from PyQt6.QtWidgets import QApplication
from ken.ui.bridge import AssistantBridge
import time
app = QApplication([])
bridge = AssistantBridge()
bridge.start_listening()
print("Started listening")
time.sleep(2)
print("Done")
