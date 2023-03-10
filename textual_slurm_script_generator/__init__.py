from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("textual-slurm-script-generator")
except PackageNotFoundError:
    # package is not installed
    pass
