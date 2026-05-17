from fastapi import APIRouter
from roof_hunter.core.targeting import generate_targets

router = APIRouter()

@router.post("/storm/targets")
def get_targets(data: dict):
    return generate_targets(
        data["properties"],
        data["storm_lat"],
        data["storm_lon"],
        data["hail_prob"]
    )
