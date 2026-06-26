from ken.ui.main_window import KenMainWindow, run_app


def create_gui():
    return KenMainWindow()


def run_gui(*args, **kwargs):
    return run_app(*args, **kwargs)
