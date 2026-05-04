from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style


def build_prompt_session() -> tuple[PromptSession, Style]:
    style = Style.from_dict({"prompt": "ansicyan bold"})
    session = PromptSession()
    return session, style
