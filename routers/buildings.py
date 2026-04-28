from fastapi import APIRouter
from data.buildings import BUILDINGS

router = APIRouter()

@router.get("/get_building_metadata")
def get_building_metadata():
  return BUILDINGS
