"""
内容提取器模块

提供多种网页内容提取方案
"""

from .base import ContentExtractor, ExtractedContent
from .jina import JinaExtractor
from .browser_extractor import BrowserExtractor

__all__ = [
    'ContentExtractor',
    'ExtractedContent',
    'JinaExtractor',
    'BrowserExtractor',
]

__version__ = '1.0.0'
