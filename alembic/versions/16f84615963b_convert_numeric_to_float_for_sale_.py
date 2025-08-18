"""convert Numeric to Float for sale/edition

Revision ID: 16f84615963b
Revises: e625f8782089
Create Date: 2025-08-16 00:00:27.879490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16f84615963b'
down_revision: Union[str, Sequence[str], None] = 'e625f8782089'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) Crear el tipo enum paymentstatus si no existe
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentstatus') THEN
            CREATE TYPE paymentstatus AS ENUM ('PENDING','PAID','CANCELLED','REFUNDED','FAILED');
          END IF;
        END
        $$;
        """
    )

    # 2) Alterar la columna payment_status usando USING para forzar el casteo.
    #    Esto es seguro aunque la tabla esté vacía.
    op.execute(
        "ALTER TABLE sale ALTER COLUMN payment_status TYPE paymentstatus USING (payment_status::paymentstatus);"
    )

    # 3) Convertir Numeric -> Float para las columnas numéricas (postgreSQL USING)
    #    Usamos op.alter_column con postgresql_using para que Postgres sepa cómo convertir.
    op.alter_column(
        "edition",
        "portion_price",
        existing_type=sa.NUMERIC(),
        type_=sa.Float(),
        postgresql_using="portion_price::double precision",
        nullable=False,  # ajustá si tu modelo permite NULL; en tu modelo original era NOT NULL
    )

    op.alter_column(
        "sale",
        "total_amount",
        existing_type=sa.NUMERIC(),
        type_=sa.Float(),
        postgresql_using="total_amount::double precision",
        nullable=False,  # ajustá según tu modelo
    )

    op.alter_column(
        "sale",
        "additional_cost",
        existing_type=sa.NUMERIC(),
        type_=sa.Float(),
        postgresql_using="additional_cost::double precision",
        existing_nullable=True,
    )

    op.alter_column(
        "sale",
        "discount_price",
        existing_type=sa.NUMERIC(),
        type_=sa.Float(),
        postgresql_using="discount_price::double precision",
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revertir Float -> Numeric(10,2). Ajustá precision/scale si necesitás otro formato.
    op.alter_column(
        "sale",
        "discount_price",
        existing_type=sa.Float(),
        type_=sa.NUMERIC(10, 2),
        postgresql_using="discount_price::numeric",
        existing_nullable=True,
    )
    op.alter_column(
        "sale",
        "additional_cost",
        existing_type=sa.Float(),
        type_=sa.NUMERIC(10, 2),
        postgresql_using="additional_cost::numeric",
        existing_nullable=True,
    )
    op.alter_column(
        "sale",
        "total_amount",
        existing_type=sa.Float(),
        type_=sa.NUMERIC(10, 2),
        postgresql_using="total_amount::numeric",
        nullable=False,
    )
    op.alter_column(
        "edition",
        "portion_price",
        existing_type=sa.Float(),
        type_=sa.NUMERIC(10, 2),
        postgresql_using="portion_price::numeric",
        nullable=False,
    )

    # Opcional: dropear el tipo enum si nadie más lo usa
    op.execute("DROP TYPE IF EXISTS paymentstatus;")
