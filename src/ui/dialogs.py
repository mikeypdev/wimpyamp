from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QLineEdit,
)
from PySide6.QtCore import QDir


class PreferencesDialog(QDialog):
    def __init__(self, parent=None, preferences=None):
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle("Preferences")
        self.setFixedSize(400, 150)

        layout = QVBoxLayout()

        # Default Music Path section
        music_path_layout = QHBoxLayout()
        music_path_label = QLabel("Default Music Path:")
        self.music_path_line_edit = QLineEdit()

        # Load current value if available
        current_path = (
            self.preferences.get_default_music_path() if self.preferences else ""
        )
        self.music_path_line_edit.setText(current_path if current_path else "")

        self.browse_music_path_btn = QPushButton("Browse...")
        self.browse_music_path_btn.clicked.connect(self.browse_music_path)

        music_path_layout.addWidget(music_path_label)
        music_path_layout.addWidget(self.music_path_line_edit)
        music_path_layout.addWidget(self.browse_music_path_btn)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(music_path_layout)
        layout.addStretch()  # Add some spacing
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def browse_music_path(self):
        """Open a directory dialog to select the default music path."""
        current_path = self.music_path_line_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Music Directory",
            current_path if current_path else QDir.homePath(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        if directory:
            self.music_path_line_edit.setText(directory)

    def accept(self):
        """Override accept to save preferences before closing."""
        if self.preferences:
            music_path = self.music_path_line_edit.text().strip()
            self.preferences.set_default_music_path(music_path)
        super().accept()


class SkinSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store reference to main window
        self.setWindowTitle("Options")
        self.setFixedSize(200, 180)  # Increased size for the additional button

        layout = QVBoxLayout()

        # Create buttons
        self.load_new_skin_btn = QPushButton("Load New Skin")
        self.load_default_skin_btn = QPushButton("Load Default Skin")
        self.preferences_btn = QPushButton(
            "Preferences..."
        )  # New button for preferences
        self.cancel_btn = QPushButton("Close")

        # Connect buttons to accept methods that set result codes
        self.load_new_skin_btn.clicked.connect(lambda: self.done(1))  # Result code 1
        self.load_default_skin_btn.clicked.connect(
            lambda: self.done(2)
        )  # Result code 2
        self.preferences_btn.clicked.connect(
            lambda: self.show_preferences_dialog()
        )  # Show preferences dialog
        self.cancel_btn.clicked.connect(lambda: self.done(0))  # Result code 0 (Cancel)

        # Add buttons to layout
        layout.addWidget(self.load_new_skin_btn)
        layout.addWidget(self.load_default_skin_btn)
        layout.addWidget(self.preferences_btn)  # Add preferences button to layout
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

    def show_preferences_dialog(self):
        """Show the preferences dialog with default music path option."""
        if self.main_window:
            dialog = PreferencesDialog(
                parent=self.main_window, preferences=self.main_window.preferences
            )
            dialog.exec_()
