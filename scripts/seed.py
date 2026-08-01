from sqlalchemy.orm import Session

from app.database import engine
from app.main import seed_database
from app.models import Base


def main() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session)
    print(f"Lantern OS seed complete on {engine.dialect.name}")


if __name__ == "__main__":
    main()
