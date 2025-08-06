"""Version information for powerloom-eigenda."""

try:
    # Try to get version from installed package
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("powerloom-eigenda")
    except PackageNotFoundError:
        # Package is not installed, use fallback
        __version__ = "0.1.0"
except ImportError:
    # Python < 3.8
    try:
        import pkg_resources

        __version__ = pkg_resources.get_distribution("powerloom-eigenda").version
    except (ImportError, pkg_resources.DistributionNotFound):
        __version__ = "0.1.0"


# Parse version info
def _parse_version_info(v):
    """Parse version string into tuple."""
    parts = v.split(".")
    # Handle dev versions like "0.1.0.dev20240101"
    if len(parts) >= 3:
        try:
            major = int(parts[0])
            minor = int(parts[1])
            # For patch, strip any dev/rc suffixes
            patch_str = parts[2].split("dev")[0].split("rc")[0].split("a")[0].split("b")[0]
            patch = int(patch_str) if patch_str else 0
            return (major, minor, patch)
        except (ValueError, IndexError):
            return (0, 1, 0)
    return (0, 1, 0)


__version_info__ = _parse_version_info(__version__)
