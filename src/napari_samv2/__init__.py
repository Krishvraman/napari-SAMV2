try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"


from ._widget import SAMV2_min

__all__ = ("SAMV2_min",)
