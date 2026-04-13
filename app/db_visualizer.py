"""
Generate an ER diagram of the Zeit database.

Outputs PNG and PDF versions to ``app/output/`` with timestamped names.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def main() -> None:
    """Render the database schema graph to disk."""
    try:
        from sqlalchemy_schemadisplay import create_schema_graph
    except ImportError as exc:  # pragma: no cover - optional utility
        raise SystemExit(
            "Install `sqlalchemy-schemadisplay` and Graphviz to use the schema visualizer."
        ) from exc

    from app.db.base import Base
    from app.db.session import engine, init_db

    init_db()

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    png_path = output_dir / f"zeit_schema_{timestamp}.png"
    pdf_path = output_dir / f"zeit_schema_{timestamp}.pdf"

    graph = create_schema_graph(
        engine,
        metadata=Base.metadata,
        show_datatypes=True,
        show_indexes=False,
        rankdir="UD",
        concentrate=False,
    )
    graph.write_png(str(png_path))
    graph.write_pdf(str(pdf_path))

    print(f"ER diagram saved:\n- {png_path}\n- {pdf_path}")


if __name__ == "__main__":
    main()
