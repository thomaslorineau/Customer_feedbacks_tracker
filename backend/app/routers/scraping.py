"""
Scraping routes for all data sources.

This module now re-exports from submodules for better organization.
"""
from .scraping.endpoints import router
from .scraping.base import set_limiter
from .scraping.jobs import _run_scrape_for_source, JOBS

# Re-export for backward compatibility
__all__ = ['router', 'set_limiter', 'JOBS', '_run_scrape_for_source']
