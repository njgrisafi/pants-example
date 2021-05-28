from dataclasses import dataclass
from typing import List

from pants.engine.rules import rule

from .import_fixer_python_target_types import ImportTarget


@dataclass(frozen=True)
class ImportStarRecommendation:
    file_path: str
    import_target: ImportTarget
    recommendations: List[ImportTarget]


@rule(desc="Gets imports * recommendations for a python target")
async def get_target_import_recommendations(source_file: str) -> ImportStarRecommendation:
    # Process imports for recommendations
    ...
