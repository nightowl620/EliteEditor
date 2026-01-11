"""
Elite Editor Entry Point
Launch the main application
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))


def setup_windows_app_id():
    try:
        if sys.platform != "win32":
            return False

        import ctypes
        from core.paths import PathManager

        paths = PathManager.instance()
        icon_path = paths.app_icon_file

        if icon_path.exists():
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "EliteEditor.App"
            )
            logger.info(f"Windows app ID set using {icon_path}")
            return True

    except Exception:
        return False

    return False


def main():
    try:
        from PySide6.QtWidgets import QApplication
        from core.app import EliteEditorApp

        setup_windows_app_id()

        app = QApplication(sys.argv)
        window = EliteEditorApp()
        window.show()

        logger.info("Elite Editor started successfully")
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(str(e))
        print(f"Error: {e}")
        print("Install dependencies with: pip install -r requirements.txt or check for local import errors")
        sys.exit(1)

    except Exception as e:
        logger.exception(str(e))
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
    