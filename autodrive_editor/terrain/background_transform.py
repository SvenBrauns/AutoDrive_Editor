from autodrive_editor.file_io.background_image import MAP_IMAGE_SIZE


class BackgroundTransform:
    """Scale and position of the background image for a map size."""

    @staticmethod
    def calculate_background_scale(map_scale, image_width=MAP_IMAGE_SIZE):
        """Metres per pixel; the map image has MAP_IMAGE_SIZE pixels at map scale 1."""

        return map_scale * MAP_IMAGE_SIZE / image_width

    @staticmethod
    def calculate_background_position(image_width, image_height, background_scale):
        position_x = -(image_width / 2) * background_scale
        position_z = -(image_height / 2) * background_scale

        return position_x, position_z
