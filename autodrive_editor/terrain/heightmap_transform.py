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
    def world_to_pixel_position(
        cls, world_x, world_z, image_width, image_height, map_scale, clamp=False
    ):
        """The pixel position as floats, between the pixel centers."""
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

        return normalized_x * (image_width - 1), normalized_z * (image_height - 1)
