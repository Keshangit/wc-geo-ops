"""Import geo-seo-claude scripts from repo root."""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_module(name: str, filename: str):
    path = _SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_fetch_page = _load_module("geo_fetch_page", "fetch_page.py")
_citability = _load_module("geo_citability", "citability_scorer.py")
_llmstxt = _load_module("geo_llmstxt", "llmstxt_generator.py")

fetch_page = _fetch_page.fetch_page
fetch_robots_txt = _fetch_page.fetch_robots_txt
fetch_llms_txt = _fetch_page.fetch_llms_txt
crawl_sitemap = _fetch_page.crawl_sitemap
extract_content_blocks = _fetch_page.extract_content_blocks

analyze_page_citability = _citability.analyze_page_citability
score_passage = _citability.score_passage

validate_llmstxt = _llmstxt.validate_llmstxt
