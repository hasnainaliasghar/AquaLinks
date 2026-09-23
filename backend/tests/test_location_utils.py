from app.utils.location import format_location_label


def _point(lng: float, lat: float) -> dict[str, object]:
    return {"type": "Point", "coordinates": [lng, lat]}


def test_formats_name_then_coords():
    label = format_location_label(name="Lake Como", centroid=_point(9.252, 45.987), digits=3)
    assert label == "Lake Como (45.987°N · 9.252°E)"


def test_avoids_duplicate_coord_suffix():
    label = format_location_label(
        name="Lake Como (45.987°N · 9.252°E)",
        centroid=_point(9.252, 45.987),
        digits=3,
    )
    assert label == "Lake Como (45.987°N · 9.252°E)"


def test_coords_only_when_no_name():
    label = format_location_label(name="", centroid=_point(8.675, 47.355), digits=3)
    assert label == "47.355°N · 8.675°E"


def test_normalizes_coords_only_name():
    label = format_location_label(
        name="47.355°N · 8.675°E", centroid=_point(8.675, 47.355), digits=3
    )
    assert label == "47.355°N · 8.675°E"
