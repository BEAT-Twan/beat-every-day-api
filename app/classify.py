def is_cycling(sport_type: str) -> bool:
    allowed = {
        "Ride", "GravelRide", "MountainBikeRide", "RoadBike", "VirtualRide",
    }
    return sport_type in allowed

def is_indoor(sport_type: str, trainer: bool) -> bool:
    return sport_type == "VirtualRide" or bool(trainer)

def is_ebike(sport_type: str) -> bool:
    return sport_type == "EBikeRide"
