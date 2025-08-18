from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db # pylint: disable=import-error
from crud import edition as crud_edition # pylint: disable=import-error
from schemas.edition import ( # pylint: disable=import-error
    EditionCreate, 
    EditionRead, 
    EditionUpdate, 
    EditionListResponse
)

router = APIRouter()

@router.get("/", response_model=EditionListResponse, summary="Listar ediciones")
def list_editions(
    q: Optional[str] = Query(None, description="Término de búsqueda (nombre o notas)"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db),
):
    return crud_edition.get_editions(db=db, q=q, limit=limit, offset=offset)


@router.get("/{edition_id}", response_model=EditionRead, summary="Obtener edición por id")
def get_edition(edition_id: int, db: Session = Depends(get_db)):
    # El CRUD ya lanza HTTPException(404) si no existe
    return crud_edition.get_edition(db, edition_id)


@router.post("/", response_model=EditionRead, status_code=status.HTTP_201_CREATED, summary="Crear edición")
def create_edition(payload: EditionCreate, db: Session = Depends(get_db)):
    edition = crud_edition.create_edition(db, payload)
    return edition


@router.patch("/{edition_id}", response_model=EditionRead, summary="Actualizar edición parcialmente")
def patch_edition(edition_id: int, payload: EditionUpdate, db: Session = Depends(get_db)):
    updated = crud_edition.update_edition(db, edition_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Edition not found")
    return updated


@router.delete("/{edition_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar edición")
def delete_edition(edition_id: int, db: Session = Depends(get_db)): # pylint: disable=useless-return
    deleted = crud_edition.delete_edition(db, edition_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Edition not found")
    return None
