import os
import sys
import json

import cv2
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QMainWindow, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QHBoxLayout, QWidget

from PIL import Image
from recognize_bricks import find_bricks, show_bricks_found

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "data"))

from config import WINDOW_NAME, DATABASE_FILE, CAMERA_INDEX, CAMERA_MAX_WIDTH, TEMP_DIRECTORY, TEMP_IMAGE_PATH

def load_database():
    print(f"Loading database from:\n{DATABASE_FILE}")
    with open(DATABASE_FILE, "r",) as file:
        database = json.load(file)

    print(f"Loaded {len(database['sets'].items())} sets.")
    return database

def get_set_name(set_data, set_id):
    possible_names = [
        set_data.get("name"),
        set_data.get("set_name"),
        set_data.get("setName"),
    ]

    for name in possible_names:
        if name:
            return str(name)

    return f"Set {set_id}"

def find_destinations(database, brick_id):
    """
    Find every set containing this part.
    Matching is based on:
        Brickognize ID == set["parts"][...]["part"]["part_num"]
    Color not used for identification.
    """

    brick_id = str(brick_id).strip()
    destinations = []
    sets = database.get("sets", {})

    for set_id, set_data in sets.items():
        for part_entry in set_data.get("parts", []):
            part = part_entry.get("part", {})
            part_num = str(part.get("part_num", "")).strip()

            if part_num != brick_id:
                continue

            color_data = part_entry.get("color", {})
            color_name = color_data.get("name", "Unknown")
            quantity = part_entry.get("quantity", 1)
            is_spare = part_entry.get("is_spare", False)
            destinations.append({
                "set_id": str(set_id),
                "set_name": get_set_name(set_data, set_id),
                "color": color_name,
                "quantity": quantity,
                "is_spare": is_spare,
            })
            # This set has this part, so we don't need to
            # inspect the rest of its parts.
            break
    return destinations

def pil_to_pixmap(image):
    image = image.convert("RGB")
    width, height = image.size
    data = image.tobytes("raw", "RGB")
    qimage = QImage(data, width, height, width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


def cv_to_pixmap(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = (frame_rgb.shape)
    bytes_per_line = (channels * width)
    image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())

class ScanWorker(QObject):
    """
    Runs Brickognize outside the GUI thread.

    This is important because find_bricks() can make many API
    requests and can therefore take several seconds.
    """
    finished = Signal(object, object)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, image_path, database):
        super().__init__()
        self.image_path = image_path
        self.database = database

    def run(self):
        try:
            self.progress.emit("Searching for bricks...")
            results = find_bricks(self.image_path)
            self.progress.emit(
                f"Found {len(results)} "
                f"brick"
                f"{'' if len(results) == 1 else 's'}"
            )

            if results:
                annotated_image = show_bricks_found(results, self.image_path)

            else:
                annotated_image = Image.open(self.image_path).convert("RGB")

            destinations = []
            for result in results:
                brick = result["items"][0]
                brick_id = str(brick["id"])
                matches = find_destinations(self.database, brick_id)
                print(
                    f"Database lookup for {brick_id}: "
                    f"{len(matches)} matches"
                )

                destinations.append(matches)

            self.finished.emit(annotated_image, (results, destinations,))

        except Exception as error:
            self.error.emit(str(error))
# ================================================================
# MAIN WINDOW
# ================================================================

class LegoSorter(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(WINDOW_NAME)
        self.resize(1500, 850)
        self.setMinimumSize(1100, 650)
        self.database = load_database()
        self.camera = cv2.VideoCapture(CAMERA_INDEX)
        if not self.camera.isOpened():
            raise RuntimeError("Could not open webcam.")

        self.current_frame = None
        self.scan_thread = None
        self.scan_worker = None
        self.scanning = False
        self.closing = False
        self.setup_ui()

        from PySide6.QtCore import QTimer

        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.update_camera)
        self.camera_timer.start(30)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("LEGO SORTER")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        left_layout.addWidget(title)

        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(500, 400)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_label.setStyleSheet(
            """
            QLabel {
                background-color: #111111;
                border: 1px solid #444444;
            }
            """
        )

        left_layout.addWidget(self.camera_label, 1)

        buttons = QHBoxLayout()
        self.scan_button = QPushButton("SCAN")
        self.scan_button.setMinimumHeight(50)
        self.scan_button.setFont(QFont("Arial", 13, QFont.Bold))
        self.scan_button.clicked.connect(self.scan)
        buttons.addWidget(self.scan_button)

        self.quit_button = QPushButton("QUIT")
        self.quit_button.setMinimumHeight(50)
        self.quit_button.clicked.connect(self.close)
        buttons.addWidget(self.quit_button)

        left_layout.addLayout(buttons)

        self.status_label = QLabel("prêt à scanner (ESPACE)")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(30)
        left_layout.addWidget(self.status_label)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        results_title = QLabel("results")
        results_title.setFont(QFont("Arial", 20, QFont.Bold))
        right_layout.addWidget(results_title)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_scroll.setWidget(self.results_container)
        right_layout.addWidget(self.results_scroll, 1)

        main_layout.addWidget(left_panel, 3)

        main_layout.addWidget(
            right_panel,
            2
        )


    # ============================================================
    # CAMERA
    # ============================================================

    def update_camera(self):
        if self.camera is None:
            return

        success, frame = (self.camera.read())

        if not success:
            return

        self.current_frame = frame
        pixmap = cv_to_pixmap(frame)
        self.display_camera_pixmap(pixmap)


    def display_camera_pixmap(self, pixmap):

        if pixmap.isNull():
            return

        scaled = pixmap.scaled(
            self.camera_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(scaled)


    def scan(self):
        if self.scanning:
            return

        if self.current_frame is None:
            self.status_label.setText("ERROR — no camera frame")
            return

        self.scanning = True
        self.scan_button.setEnabled(False)
        self.scan_button.setText("SCANNING...")
        self.status_label.setText("Capturing image...")

        os.makedirs(TEMP_DIRECTORY, exist_ok=True)

        frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        image.save(TEMP_IMAGE_PATH, quality=95)
        self.clear_results()

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(TEMP_IMAGE_PATH, self.database)
        self.scan_worker.moveToThread(self.scan_thread)

        # Thread starts -> worker starts.
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self.scan_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.thread_finished)
        self.scan_thread.start()

    def thread_finished(self):
        """
        Called only after the QThread has actually stopped.
        This is the important part that prevents: QThread: Destroyed while thread is still running
        """

        thread = self.scan_thread
        self.scan_thread = None
        self.scan_worker = None
        self.scanning = False

        self.scan_button.setEnabled(True)
        self.scan_button.setText("SCAN BRICKS")

        if thread is not None:
            thread.deleteLater()

    def scan_progress(self, message):
        self.status_label.setText(message)

    def scan_finished(self, annotated_image, data):
        results, destinations = data
        # Show annotated image.
        pixmap = pil_to_pixmap(annotated_image)
        self.display_camera_pixmap(pixmap)
        # Show results.
        self.display_results(results, destinations)
        count = len(results)

        self.status_label.setText(
            f"FOUND {count} BRICK"
            f"{'' if count == 1 else 'S'} "
            f"— press SPACE to scan again"
        )

    def scan_error(self, message):

        print(f"Scan error: {message}")
        self.status_label.setText(f"ERROR: {message}")

    def finish_scan(self):

        self.scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("SCAN BRICKS")
        self.scan_thread = None
        self.scan_worker = None

    def clear_results(self):
        while self.results_layout.count():
            item = (self.results_layout.takeAt(0))
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


    def display_results(self, results, destinations):

        if not results:
            label = QLabel("No bricks detected.")
            label.setFont(QFont("Arial", 14))
            self.results_layout.addWidget(label)
            return

        for index, result in enumerate(results):
            matches = destinations[index]
            self.add_brick_card(index + 1, result, matches)

    def add_brick_card(self, number, result, matches):
        brick = result["items"][0]
        brick_id = brick["id"]
        brick_name = brick["name"]
        confidence = brick.get("score", 0)

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            """
            QFrame {
                background-color: #f4f4f4;
                border: 1px solid #cccccc;
                border-radius: 6px;
            }
            """
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        title = QLabel(f"{number}. {brick_id} — {brick_name}")
        title.setWordWrap(True)
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        confidence_label = QLabel(
            f"Brickognize confidence: "
            f"{confidence:.0%}"
        )

        confidence_label.setStyleSheet("color: #555555;")
        layout.addWidget(confidence_label)

        if not matches:
            no_match = QLabel("no match :(")
            no_match.setFont(QFont("Arial", 11, QFont.Bold))
            no_match.setStyleSheet("color: #aa0000;")
            no_match.setWordWrap(True)
            layout.addWidget(no_match)

        elif len(matches) == 1:
            self.add_single_destination(layout, matches[0])

        else:
            possible = QLabel(f"{len(matches)} possible sets")
            possible.setFont(QFont("Arial", 11, QFont.Bold))
            layout.addWidget(possible)
            # Don't make a gigantic card if a very common brick
            # occurs in many sets.
            for match in matches[:15]:
                self.add_multiple_destination(layout, match)

            if len(matches) > 15:
                more = QLabel(
                    f"... and "
                    f"{len(matches) - 15} more")
                more.setStyleSheet("color: #666666;")
                layout.addWidget(more)

        self.results_layout.addWidget(card)


    def add_single_destination(self, layout, match):

        set_id = match["set_id"]
        set_name = match["set_name"]

        color = match["color"]
        quantity = match["quantity"]
        is_spare = match["is_spare"]

        destination = QLabel(
            f"→ SET {set_id}-1\n"
            f"   {set_name}\n"
            f"   {color} ×{quantity}"
            f"{' (spare)' if is_spare else ''}"
        )

        destination.setWordWrap(True)
        destination.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(destination)

    def add_multiple_destination(self, layout, match):
        set_id = match["set_id"]
        set_name = match["set_name"]
        color = match["color"]
        quantity = match["quantity"]
        is_spare = match["is_spare"]

        label = QLabel(
            f"→ {set_id}-1\n"
            f"   {set_name}\n"
            f"   {color} ×{quantity}"
            f"{' (spare)' if is_spare else ''}"
        )

        label.setWordWrap(True)
        layout.addWidget(label)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if not self.scanning:
                self.scan()
            event.accept()
            return

        if event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closing = True
        if hasattr(self, "camera_timer"):
            self.camera_timer.stop()

        # Release camera.
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            
        # If a Brickognize worker is still running,
        # wait for it to finish before destroying the GUI.
        if self.scan_thread is not None:
            if self.scan_thread.isRunning():
                self.status_label.setText("Finishing scan...")
                self.scan_thread.quit()
                self.scan_thread.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LEGO Sorter")
    window = LegoSorter()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()