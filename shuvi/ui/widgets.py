from qtpy.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget


class SelectorWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("Enter a path or browse it")

        self.browse_btn = QPushButton("...", self)
        self.browse_btn.setMaximumWidth(40)
        self.browse_btn.clicked.connect(self.browse)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.browse_btn)

    def select(self) -> str:
        raise NotImplementedError

    def browse(self):
        path = self.select()
        if path:
            self.line_edit.setText(path)

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, path: str):
        self.line_edit.setText(path)


class FolderSelectorWidget(SelectorWidget):
    def select(self) -> str:
        return QFileDialog.getExistingDirectory(self, "Select a folder", self.line_edit.text())


class FileSelectorWidget(SelectorWidget):
    def __init__(self, filters: str = "All Files (*)", parent: QWidget | None = None):
        super().__init__(parent)
        self.filters = filters

    def select(self) -> str:
        path, _ = QFileDialog.getOpenFileName(self, "Select a file", self.line_edit.text(), self.filters)
        return path


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication()
    w = QWidget()
    l = QHBoxLayout(w)

    f = FolderSelectorWidget()
    l.addWidget(f)

    w.show()

    sys.exit(app.exec())
