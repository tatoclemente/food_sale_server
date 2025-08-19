from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db  # pylint: disable=import-error, unused-import
from crud import edition_ingredient as crud_ei  # pylint: disable=import-error, unused-import
from schemas.edition_ingredient import (  # pylint: disable=import-error, unused-import
    EditionIngredientCreate,
    EditionIngredientRead,
    EditionIngredientListResponse,
    EditionIngredientUpdate,
)

router = APIRouter()


@router.get("/{edition_id}", 
            response_model=EditionIngredientListResponse, 
            summary="Listar ingredientes por edición")
def list_edition_ingredients(
    edition_id: int,
    q: Optional[str] = Query(None, description="Término de búsqueda (notes)"),
    categories: Optional[str] = Query(None, description="Filtrar por categorías (MEAT,VEGETABLES)"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db)):
    return crud_ei.get_edition_ingredients( db=db, 
                                            edition_id=edition_id, 
                                            q=q, 
                                            categories=categories,
                                            limit=limit, 
                                            offset=offset )


@router.get("/{ei_id}", 
            response_model=EditionIngredientRead, 
            summary="Obtener ingredient-edition por id")
def get_edition_ingredient(ei_id: int, db: Session = Depends(get_db)):
    return crud_ei.get_edition_ingredient(db, ei_id)


@router.post(
    "/{edition_id}",
    response_model=EditionIngredientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar ingredient a una edición"
)
def create_edition_ingredient(edition_id: int, 
                              payload: EditionIngredientCreate, 
                              db: Session = Depends(get_db)):
    return crud_ei.create_edition_ingredient(db, edition_id, payload)


@router.patch(
    "/{ei_id}",
    response_model=EditionIngredientRead,
    summary="Actualizar ingredient-edition parcialmente"
)
def patch_edition_ingredient(ei_id: int, 
                             payload: EditionIngredientUpdate, 
                             db: Session = Depends(get_db)):
    updated = crud_ei.update_edition_ingredient(db, ei_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="EditionIngredient not found")
    return updated


@router.delete(
    "/{ei_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar ingredient de una edición"
)
def delete_edition_ingredient(ei_id: int, db: Session = Depends(get_db)):  # pylint: disable=useless-return
    deleted = crud_ei.delete_edition_ingredient(db, ei_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="EditionIngredient not found")
    return None
