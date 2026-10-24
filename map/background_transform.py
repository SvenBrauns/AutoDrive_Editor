class MapTransform:

    @staticmethod
    def calculate_background_scale(map_scale):
        return float(map_scale)

    @staticmethod
    def calculate_background_position(
        image_width,
        image_height,
        map_scale
    ):
        position_x = -(image_width / 2) * map_scale
        position_z = -(image_height / 2) * map_scale

        return position_x, position_z