from fastapi import FastAPI
from core.config import settings
from api.routes import customer, sale, edition, ingredient, purchase, edition_ingredient

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(customer.router, prefix="/customers", tags=["Clientes (customers)"])
app.include_router(edition.router, prefix="/editions", tags=["Ediciones (editions)"])
app.include_router(sale.router, prefix="/sales", tags=["Ventas (sales)"])
app.include_router(ingredient.router, prefix="/ingredients", tags=["Ingredientes (ingredients)"])
app.include_router(purchase.router, prefix="/purchases", tags=["Compras (purchases)"])
app.include_router(edition_ingredient.router, prefix="/edition_ingredients", tags=["Ingredientes por edición (edition_ingredients)"])
