from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db # pylint: disable=import-error, unused-import
from crud import ingredient as crud_ingredient # pylint: disable=import-error, unused-import
from schemas.ingredient import ( # pylint: disable=import-error, unused-import
    IngredientCreate, 
    IngredientRead, 
    IngredientListResponse, 
    IngredientUpdate,
)

router = APIRouter()


@router.get("/", response_model=IngredientListResponse, summary="Listar ingredientes")
def list_ingredients(
    q: Optional[str] = Query(None, description="Término de búsqueda (nombre, unidad o categoría)"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db),
):
    return crud_ingredient.get_ingredients(db=db, q=q, limit=limit, offset=offset)


@router.get("/{ingredient_id}", response_model=IngredientRead, summary="Obtener ingrediente por id")
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    # El CRUD ya lanza HTTPException(404) si no existe
    return crud_ingredient.get_ingredient(db, ingredient_id)


@router.post(
    "/", 
    response_model=IngredientRead, 
    status_code=status.HTTP_201_CREATED, 
    summary="Crear ingrediente"
)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    ingredient = crud_ingredient.create_ingredient(db, payload)
    return ingredient


@router.patch(
    "/{ingredient_id}", 
    response_model=IngredientRead, 
    summary="Actualizar ingrediente parcialmente"
)
def patch_ingredient(ingredient_id: int, payload: IngredientUpdate, db: Session = Depends(get_db)):
    updated = crud_ingredient.update_ingredient(db, ingredient_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return updated


@router.delete(
    "/{ingredient_id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Eliminar ingrediente"
)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)): # pylint: disable=useless-return
    deleted = crud_ingredient.delete_ingredient(db, ingredient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return None
