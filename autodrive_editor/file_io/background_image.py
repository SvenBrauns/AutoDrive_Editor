from PIL import Image
from PySide6.QtGui import QImage, QPixmap


def load_dds_as_pixmap(file_path):

    image = Image.open(file_path)

    image = image.convert("RGBA")

    width, height = image.size

    image = image.crop((width // 4, height // 4, width * 3 // 4, height * 3 // 4))

    width, height = image.size

    data = image.tobytes("raw", "RGBA")

    qimage = QImage(data, width, height, QImage.Format_RGBA8888)

    return QPixmap.fromImage(qimage)
