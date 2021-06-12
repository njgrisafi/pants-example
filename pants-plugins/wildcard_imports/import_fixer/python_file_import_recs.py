import re
from dataclasses import dataclass
from typing import Optional, Tuple

from pants.engine.fs import FileContent
from wildcard_imports.import_fixer import utils
from wildcard_imports.import_fixer.python_file_info import PythonFileInfo, PythonImport


@dataclass(frozen=True)
class PythonImportRecommendation:
    source_import: Optional[PythonImport]
    recommendations: Tuple[PythonImport, ...]


@dataclass(frozen=True)
class PythonFileImportRecommendations:
    py_file_info: PythonFileInfo
    import_recommendations: Tuple[PythonImportRecommendation, ...]

    @property
    def fixed_file_content(self) -> FileContent:
        content = self.py_file_info.file_content_str
        for import_rec in self.import_recommendations:
            # Replace source import with recs
            if import_rec.source_import:
                regex_str = import_rec.source_import.import_str.replace("*", "\*")  # noqa: W605
                if len(import_rec.recommendations) == 0:
                    content = re.sub(f"{regex_str}\n", "", content)
                else:
                    # print(import_rec.recommendations)
                    replacement_import_strs = set([py_import.import_str for py_import in import_rec.recommendations])
                    content = re.sub(regex_str, "\n".join(replacement_import_strs), content)
            # Add new import recs
            elif len(import_rec.recommendations) > 0:
                import_matches = utils.get_top_level_import_matches(content)
                insert_line = import_matches[-1].span()[1] if len(import_matches) > 0 else 0
                import_content_to_insert = "\n".join([py_import.import_str for py_import in import_rec.recommendations])
                content = content[:insert_line] + f"\n{import_content_to_insert}\n" + content[insert_line:]
        return FileContent(path=self.py_file_info.path, content=content.encode())

