import xml.etree.ElementTree as ET

from pathlib import Path

from autodrive.models import AutoDriveData, MarkerData, NodeData


class AutoDriveXmlParser:
    @classmethod
    def load(cls, file_path) -> AutoDriveData:
        xml_path = Path(file_path).resolve()

        if not xml_path.is_file():
            raise FileNotFoundError(f"Die AutoDrive-XML wurde nicht gefunden: {xml_path}")

        try:
            tree = ET.parse(xml_path)

        except ET.ParseError as ex:
            raise ValueError(f"Die XML-Datei ist ungültig: {ex}") from ex

        root = tree.getroot()

        waypoint_section = root.find("waypoints")

        if waypoint_section is None:
            raise ValueError("Die XML enthält keinen Waypoint-Bereich.")

        x_values = cls._parse_float_values(waypoint_section, "x")

        y_values = cls._parse_float_values(waypoint_section, "y")

        z_values = cls._parse_float_values(waypoint_section, "z")

        node_count = cls._validate_coordinate_lengths(x_values, y_values, z_values)

        flag_values = cls._parse_flag_values(waypoint_section, node_count)

        outgoing_values = cls._parse_connection_values(waypoint_section, "out", node_count)

        incoming_values = cls._parse_connection_values(waypoint_section, "in", node_count)

        autodrive_data = AutoDriveData()

        for index in range(node_count):
            node_id = index + 1

            node = NodeData(
                node_id=node_id,
                x=x_values[index],
                y=y_values[index],
                z=z_values[index],
                flag=flag_values[index],
                outgoing=outgoing_values[index],
                incoming=incoming_values[index],
            )

            autodrive_data.add_node(node)

        cls._parse_markers(root, autodrive_data)

        return autodrive_data

    @staticmethod
    def _parse_float_values(waypoint_section, element_name):
        element = waypoint_section.find(element_name)

        if element is None or not element.text:
            raise ValueError(f"Die XML enthält keine {element_name}-Koordinaten.")

        values = []

        for raw_value in element.text.split(";"):
            raw_value = raw_value.strip()

            if not raw_value:
                continue

            try:
                values.append(float(raw_value))

            except ValueError as ex:
                raise ValueError(
                    f"Ungültiger Wert im Element '{element_name}': {raw_value}"
                ) from ex

        if not values:
            raise ValueError(f"Das XML-Element '{element_name}' enthält keine gültigen Werte.")

        return values

    @staticmethod
    def _validate_coordinate_lengths(x_values, y_values, z_values):
        lengths = {"x": len(x_values), "y": len(y_values), "z": len(z_values)}

        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"Die Anzahl der X-, Y- und Z-Koordinaten stimmt nicht überein: {lengths}"
            )

        return len(x_values)

    @staticmethod
    def _parse_flag_values(waypoint_section, node_count):
        flags_element = waypoint_section.find("flags")

        if flags_element is None or not flags_element.text:
            return [0 for _ in range(node_count)]

        raw_flags = flags_element.text.split(";")
        flags = []

        for raw_flag in raw_flags:
            raw_flag = raw_flag.strip()

            if not raw_flag:
                continue

            try:
                flags.append(int(raw_flag))

            except ValueError as ex:
                raise ValueError(f"Ungültiger Node-Flag: {raw_flag}") from ex

        if len(flags) < node_count:
            flags.extend([0] * (node_count - len(flags)))

        return flags[:node_count]

    @classmethod
    def _parse_connection_values(cls, waypoint_section, element_name, node_count):
        connection_element = waypoint_section.find(element_name)

        if connection_element is None or connection_element.text is None:
            return [set() for _ in range(node_count)]

        raw_entries = connection_element.text.split(";")
        parsed_entries = []

        for raw_entry in raw_entries:
            parsed_entries.append(cls._parse_connection_entry(raw_entry))

        if len(parsed_entries) < node_count:
            parsed_entries.extend(set() for _ in range(node_count - len(parsed_entries)))

        return parsed_entries[:node_count]

    @staticmethod
    def _parse_connection_entry(raw_entry):
        connections = set()

        if not raw_entry:
            return connections

        for raw_node_id in raw_entry.split(","):
            raw_node_id = raw_node_id.strip()

            if not raw_node_id:
                continue

            try:
                node_id = int(raw_node_id)

            except ValueError as ex:
                raise ValueError(f"Ungültige Verbindungs-ID: {raw_node_id}") from ex

            if node_id <= 0:
                continue

            connections.add(node_id)

        return connections

    @staticmethod
    def _parse_markers(root, autodrive_data):
        markers_section = root.find("markers")

        if markers_section is None:
            return

        for marker_element in markers_section:
            raw_node_id = marker_element.attrib.get("i")

            if not raw_node_id:
                continue

            try:
                node_id = int(raw_node_id)

            except ValueError:
                continue

            if node_id not in autodrive_data.nodes:
                continue

            marker = MarkerData(
                node_id=node_id,
                name=marker_element.attrib.get("n", ""),
                group=marker_element.attrib.get("g", ""),
            )

            autodrive_data.add_marker(marker)
