"""
Media resolver package.

Resolvers are responsible for converting supported public
platform URLs into normalized media information.

Supported platforms:
- TeraBox
- Instagram

Platform-specific implementation lives in:
    resolvers.terabox
    resolvers.instagram
"""

from .terabox import TeraBoxResolver
from .instagram import InstagramResolver


__all__ = [
    "TeraBoxResolver",
    "InstagramResolver",
]
