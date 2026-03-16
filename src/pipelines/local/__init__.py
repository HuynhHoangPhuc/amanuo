"""Local extraction pipeline."""

import importlib

_local = importlib.import_module("src.pipelines.local.local-provider")
LocalProvider = _local.LocalProvider
