# config.py
CONCRETE_TYPES = {
    "Type I": 24,    # Normal Portland, base curing time in hours
    "Type II": 26,   # Moderate sulfate resistance
    "Type III": 12,  # High early strength
    "Type V": 28,    # High sulfate resistance
    "Lightweight": 20  # Lightweight concrete
}

PAINT_TYPES = {
    "Acrylic": 4,    # Base drying time in hours
    "Oil-Based": 6,  # Base drying time in hours
    "Water-Based": 3  # Base drying time in hours
}

# Weather thresholds for optimal conditions
WEATHER_THRESHOLD_TEMP_MIN = 5    # Minimum temperature in Celsius (5°C)
WEATHER_THRESHOLD_TEMP_MAX = 35   # Maximum temperature in Celsius (35°C)
WEATHER_THRESHOLD_HUMIDITY_MAX = 80  # Maximum humidity percentage (80%)
WEATHER_THRESHOLD_RAIN = 0       # Maximum rain in mm (0 mm for no rain)