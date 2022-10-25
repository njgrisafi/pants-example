from pants.backend.python.target_types import (
    PythonSourcesGeneratorTarget,
    PythonSourceTarget,
    PythonTestsGeneratorTarget,
    PythonTestTarget,
    PythonTestUtilsGeneratorTarget,
)
from pants.engine.target import BoolField, StringSequenceField


class SkipExternalImportInfer(BoolField):
    alias = "skip_external_import_infer"
    default = False
    help = "If true, don't run infer imports from external target's code."


class SkipModuleImportInfer(BoolField):
    alias = "skip_module_import_infer"
    default = False
    help = "If true, don't run infer imports from the same module target's code."


class SkipSelfImportInfer(BoolField):
    alias = "skip_self_import_infer"
    default = False
    help = "If true, don't run infer imports for this target's code."


class SkipImportInfer(BoolField):
    alias = "skip_import_infer"
    default = False
    help = "If true, will disable all import inference."


class GlobDependencies(StringSequenceField):
    alias = "glob_dependencies"
    default = []
    help = "Set to use a glob to include in dependencies on this target's code."


def rules():
    return [
        PythonSourcesGeneratorTarget.register_plugin_field(SkipExternalImportInfer),
        PythonSourceTarget.register_plugin_field(SkipExternalImportInfer),
        PythonTestsGeneratorTarget.register_plugin_field(SkipExternalImportInfer),
        PythonTestTarget.register_plugin_field(SkipExternalImportInfer),
        PythonTestUtilsGeneratorTarget.register_plugin_field(SkipExternalImportInfer),
        PythonSourcesGeneratorTarget.register_plugin_field(SkipSelfImportInfer),
        PythonSourceTarget.register_plugin_field(SkipSelfImportInfer),
        PythonTestsGeneratorTarget.register_plugin_field(SkipSelfImportInfer),
        PythonTestTarget.register_plugin_field(SkipSelfImportInfer),
        PythonTestUtilsGeneratorTarget.register_plugin_field(SkipSelfImportInfer),
        PythonSourcesGeneratorTarget.register_plugin_field(SkipImportInfer),
        PythonSourceTarget.register_plugin_field(SkipImportInfer),
        PythonTestsGeneratorTarget.register_plugin_field(SkipImportInfer),
        PythonTestTarget.register_plugin_field(SkipImportInfer),
        PythonTestUtilsGeneratorTarget.register_plugin_field(SkipImportInfer),
        PythonSourcesGeneratorTarget.register_plugin_field(SkipModuleImportInfer),
        PythonSourceTarget.register_plugin_field(SkipModuleImportInfer),
        PythonTestsGeneratorTarget.register_plugin_field(SkipModuleImportInfer),
        PythonTestTarget.register_plugin_field(SkipModuleImportInfer),
        PythonTestUtilsGeneratorTarget.register_plugin_field(SkipModuleImportInfer),
        PythonSourcesGeneratorTarget.register_plugin_field(GlobDependencies),
        PythonSourceTarget.register_plugin_field(GlobDependencies),
        PythonTestsGeneratorTarget.register_plugin_field(GlobDependencies),
        PythonTestTarget.register_plugin_field(GlobDependencies),
        PythonTestUtilsGeneratorTarget.register_plugin_field(GlobDependencies),
    ]
