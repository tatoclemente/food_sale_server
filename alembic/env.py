import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# 1️⃣ Agregar src al PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# 3️⃣ Importar Base después de agregar src al path
from db.base import Base  # pylint: disable=import-error, wrong-import-position
from models.customer import Customer  # pylint: disable=import-error, unused-import, wrong-import-position
from models.edition import Edition  # pylint: disable=import-error, unused-import, wrong-import-position
from models.sale import Sale  # pylint: disable=import-error, unused-import, wrong-import-position
from models.purchase import Purchase  # pylint: disable=import-error, unused-import, wrong-import-position
from models.ingredient import Ingredient  # pylint: disable=import-error, unused-import, wrong-import-position
from models.edition_ingredient import EditionIngredient  # pylint: disable=import-error, unused-import, wrong-import-position

# 2️⃣ Cargar variables de entorno
load_dotenv()

# 4️⃣ Configuración Alembic
config = context.config # pylint: disable=no-member
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure( # pylint: disable=no-member
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction(): # pylint: disable=no-member
        context.run_migrations() # pylint: disable=no-member


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure( # pylint: disable=no-member
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction(): # pylint: disable=no-member
            context.run_migrations() # pylint: disable=no-member


if context.is_offline_mode(): # pylint: disable=no-member
    run_migrations_offline()
else:
    run_migrations_online()
