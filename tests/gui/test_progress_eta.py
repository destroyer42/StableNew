import pytest
from src.gui.main_window import MainWindow 
 
def test_progress_eta_display(monkeypatch): 
    """Ensure progress/ETA fields update via controller callbacks.""" 
    win = MainWindow() 
    # TODO: simulate controller progress event and assert status text changes 
