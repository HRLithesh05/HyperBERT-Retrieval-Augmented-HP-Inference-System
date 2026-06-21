import argparse
import json
from pathlib import Path

from pipeline import Pipeline


ALL_STEPS = [
    "collect", "enrich", "download", "extract",
    "refine", "qc",
    "hp_extract", "faiss", "rscore",
]


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Module 0 corpus builder")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    parser.add_argument(
        "--steps",
        default="all",
        choices=ALL_STEPS + ["all"],
        help="Pipeline steps to run",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    config = load_config(config_path)
    pipeline = Pipeline(config)

    step = args.steps

    # ---- original steps ----
    if step in ("collect", "all"):
        pipeline.collect_metadata()
    if step in ("enrich", "all"):
        pipeline.enrich_pdfs()
    if step in ("download", "all"):
        pipeline.download_pdfs()
    if step in ("extract", "all"):
        pipeline.extract_text()
    if step in ("refine", "all"):
        pipeline.refine_domain()
    if step in ("qc", "all"):
        pipeline.qc_and_export()

    # ---- new steps (3, 4, 5) ----
    if step in ("hp_extract", "all"):
        pipeline.extract_hyperparams()
    if step in ("faiss", "all"):
        pipeline.build_faiss_index()
    if step in ("rscore", "all"):
        pipeline.compute_rscores()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
