"""
Generate an ER diagram of the Zeit Project database using SQLAlchemy SchemaDisplay.
Outputs both PNG and PDF versions inside ./output/ with timestamps.
"""

from pathlib import Path
import sys
import datetime

# --- Resolve project root and add to sys.path ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))  # allow "from app.db..." imports

# --- Imports ---
from sqlalchemy_schemadisplay import create_schema_graph
from app.db.session import engine, init_db
from app.db.base import Base


# --- Ensure the DB schema exists before visualization ---
init_db()

# --- Prepare output directory ---
output_dir = current_dir / "output"
output_dir.mkdir(exist_ok=True)

# --- Timestamped output file names ---
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
png_path = output_dir / f"zeit_schema_{timestamp}.png"
pdf_path = output_dir / f"zeit_schema_{timestamp}.pdf"

# --- Generate schema graph ---
graph = create_schema_graph(
    engine,                     # first positional arg = engine (required)
    metadata=Base.metadata,
    show_datatypes=True,
    show_indexes=False,
    rankdir="UD",               # layout left to right
    concentrate=False,
)

# --- Save outputs ---
graph.write_png(str(png_path))
graph.write_pdf(str(pdf_path))

print(f"ER diagram saved:\n- {png_path}\n- {pdf_path}")