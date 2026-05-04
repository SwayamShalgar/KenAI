import datetime
import subprocess
from typing import Optional, Tuple


def route_command(text: str) -> Tuple[bool, Optional[str]]:
    """
    Returns (is_handled, response_string)
    """
    text_lower = text.strip().lower()

    if text_lower in ["tell time", "what time is it", "time"]:
        now = datetime.datetime.now().strftime("%I:%M %p, %A, %B %d")
        return True, f"The current time is {now}."

    if text_lower.startswith("open youtube"):
        subprocess.Popen(
            ["xdg-open", "https://youtube.com"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, "Opening YouTube in your default browser..."

    if text_lower.startswith("open browser"):
        subprocess.Popen(
            ["xdg-open", "about:blank"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, "Opening your browser..."

    if text_lower.startswith("open vscode") or text_lower.startswith("open code"):
        subprocess.Popen(["code"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Opening Visual Studio Code..."

    if text_lower == "sleep":
        subprocess.Popen(["systemctl", "suspend"])
        return True, "Going to sleep now..."

    if text_lower == "shutdown":
        subprocess.Popen(["systemctl", "poweroff"])
        return True, "Shutting down the system. Goodbye!"

    return False, None
