from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from core.config import settings
from api.routes import customer, sale, edition, ingredient, purchase, edition_ingredient

app = FastAPI(title=settings.app_name, version=settings.app_version)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(customer.router, prefix="/customers", tags=["Clientes (customers)"])
app.include_router(edition.router, prefix="/editions", tags=["Ediciones (editions)"])
app.include_router(sale.router, prefix="/sales", tags=["Ventas (sales)"])
app.include_router(ingredient.router, prefix="/ingredients", tags=["Ingredientes (ingredients)"])
app.include_router(purchase.router, prefix="/purchases", tags=["Compras (purchases)"])
app.include_router(edition_ingredient.router, prefix="/edition_ingredients", tags=["Ingredientes por edición (edition_ingredients)"])
