from PySide6.QtWidgets import QMessageBox, QWidget

APP_TITLE = "AutoDrive FS25 Editor"


def inform(parent: QWidget, message: str):
    QMessageBox.information(parent, APP_TITLE, message)
