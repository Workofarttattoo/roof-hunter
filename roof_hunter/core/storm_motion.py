import math

def project_storm_cell(cell, minutes=30):
    lat = cell["center_lat"]
    lon = cell["center_lon"]

    speed = cell.get("speed_kmh", 40)
    direction = cell.get("direction_deg", 90)

    dx = speed * math.cos(math.radians(direction)) * (minutes / 60)
    dy = speed * math.sin(math.radians(direction)) * (minutes / 60)

    new_lat = lat + dy / 111
    new_lon = lon + dx / (111 * math.cos(math.radians(lat)))

    return new_lat, new_lon
