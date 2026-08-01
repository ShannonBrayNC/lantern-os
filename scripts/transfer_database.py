from __future__ import annotations

import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    KPI,
    Base,
    Milestone,
    Opportunity,
    ResearchProgram,
    SchemaMeta,
    Setting,
    Task,
)

MODELS = (SchemaMeta, Setting, KPI, Task, Opportunity, ResearchProgram, Milestone)


def transfer(source_url: str, target_url: str) -> None:
    source = create_engine(source_url)
    target = create_engine(target_url)
    Base.metadata.create_all(target)

    with Session(source) as source_session, Session(target) as target_session:
        for model in MODELS:
            target_session.query(model).delete()
            for item in source_session.scalars(select(model)).all():
                values = {
                    column.name: getattr(item, column.name)
                    for column in model.__table__.columns
                }
                target_session.add(model(**values))
        target_session.commit()

    print(
        f"Transferred Lantern OS data from {source.dialect.name} "
        f"to {target.dialect.name}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transfer Lantern OS data between SQLAlchemy databases."
    )
    parser.add_argument("--source", required=True, help="Source SQLAlchemy database URL")
    parser.add_argument("--target", required=True, help="Target SQLAlchemy database URL")
    args = parser.parse_args()
    transfer(args.source, args.target)


if __name__ == "__main__":
    main()
