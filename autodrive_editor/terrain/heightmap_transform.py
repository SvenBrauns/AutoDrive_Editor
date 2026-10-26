from autodrive_editor.i18n import tr


class HeightmapTransform:
    """Converts between map positions and heightmap pixels."""

    BASE_MAP_SIZE = 2048

    @classmethod
    def calculate_world_size(cls, map_scale):
        map_scale = float(map_scale)

        if map_scale <= 0:
            raise ValueError(tr("The map scale must be greater than 0."))

        return cls.BASE_MAP_SIZE * map_scale

    @classmethod
    def calculate_units_per_pixel(cls, image_size, map_scale):
        image_size = int(image_size)

        if image_size < 2:
            raise ValueError(tr("The heightmap needs at least two pixels per axis."))

        world_size = cls.calculate_world_size(map_scale)

        pixel_intervals = image_size - 1

        return world_size / pixel_intervals

    @classmethod
    def world_to_pixel(cls, world_x, world_z, image_width, image_height, map_scale, clamp=False):
        image_width = int(image_width)

        image_height = int(image_height)

        if image_width < 2 or image_height < 2:
            raise ValueError(tr("The heightmap must be at least 2 × 2 pixels."))

        world_size = cls.calculate_world_size(map_scale)

        half_world_size = world_size / 2

        normalized_x = (float(world_x) + half_world_size) / world_size

        normalized_z = (float(world_z) + half_world_size) / world_size

        if not clamp:
            if normalized_x < 0 or normalized_x > 1:
                raise ValueError(tr("The X coordinate {value} is outside the map.", value=world_x))

            if normalized_z < 0 or normalized_z > 1:
                raise ValueError(tr("The Z coordinate {value} is outside the map.", value=world_z))

        normalized_x = max(0.0, min(normalized_x, 1.0))

        normalized_z = max(0.0, min(normalized_z, 1.0))

        pixel_x_float = normalized_x * (image_width - 1)

        pixel_y_float = normalized_z * (image_height - 1)

        pixel_x = round(pixel_x_float)

        pixel_y = round(pixel_y_float)

        return pixel_x, pixel_y

    @classmethod
    def pixel_to_world(cls, pixel_x, pixel_y, image_width, image_height, map_scale):
        image_width = int(image_width)

        image_height = int(image_height)

        if image_width < 2 or image_height < 2:
            raise ValueError(tr("The heightmap must be at least 2 × 2 pixels."))

        pixel_x = int(pixel_x)

        pixel_y = int(pixel_y)

        if pixel_x < 0 or pixel_x >= image_width:
            raise ValueError(
                tr("The pixel X coordinate {value} is outside the heightmap.", value=pixel_x)
            )

        if pixel_y < 0 or pixel_y >= image_height:
            raise ValueError(
                tr("The pixel Y coordinate {value} is outside the heightmap.", value=pixel_y)
            )

        normalized_x = pixel_x / (image_width - 1)

        normalized_y = pixel_y / (image_height - 1)

        world_size = cls.calculate_world_size(map_scale)

        half_world_size = world_size / 2

        world_x = normalized_x * world_size - half_world_size

        world_z = normalized_y * world_size - half_world_size

        return world_x, world_z
