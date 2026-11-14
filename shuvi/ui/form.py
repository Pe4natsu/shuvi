from qtpy.QtWidgets import QFormLayout, QLineEdit, QWidget

from shuvi.ui.widgets import FolderSelectorWidget


class ShuviForm(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QFormLayout()
        self.setLayout(layout)

        self.url = QLineEdit(self)
        layout.addRow("URL", self.url)

        self.folder = FolderSelectorWidget(self)
        layout.addRow("Output Folder", self.folder)


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ShuviForm()
    w.show()
    sys.exit(app.exec())
