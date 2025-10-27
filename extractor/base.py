"""
内容提取器基类模块

定义了内容提取器的抽象接口和通用数据结构
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ExtractedContent:
    """提取的内容数据结构"""
    url: str                    # 原始 URL
    title: str                  # 文章标题
    content: str                # 文章正文（Markdown 格式）
    platform: str               # 平台名称（如：知乎、掘金）
    platform_logo: str          # 平台 Logo URL
    author: Optional[str] = None        # 作者名（可选）
    publish_date: Optional[str] = None  # 发布日期（可选）
    word_count: int = 0         # 字数统计
    success: bool = True        # 是否提取成功
    error: Optional[str] = None # 错误信息
    extract_time: str = None    # 提取时间
    processing_time: Optional[float] = None  # 处理耗时（秒）
    
    def __post_init__(self):
        """初始化后处理"""
        if self.extract_time is None:
            self.extract_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.content:
            self.word_count = len(self.content)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    def to_simple_dict(self) -> Dict:
        """转换为简化字典（用于日志输出）"""
        return {
            'url': self.url,
            'title': self.title[:50] + '...' if len(self.title) > 50 else self.title,
            'platform': self.platform,
            'word_count': self.word_count,
            'success': self.success,
            'error': self.error
        }


class ContentExtractor(ABC):
    """内容提取器抽象基类"""
    
    def __init__(self, timeout: int = 30):
        """
        初始化提取器
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.name = self.__class__.__name__
    
    @abstractmethod
    def extract(self, url: str) -> ExtractedContent:
        """
        提取网页内容（核心方法，子类必须实现）
        
        Args:
            url: 目标网址
            
        Returns:
            ExtractedContent: 提取的内容对象
        """
        pass
    
    def extract_batch(self, urls: List[str]) -> List[ExtractedContent]:
        """
        批量提取内容
        
        Args:
            urls: URL 列表
            
        Returns:
            List[ExtractedContent]: 提取结果列表
        """
        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 正在提取: {url}")
            try:
                result = self.extract(url)
                results.append(result)
                status = "成功" if result.success else f"失败: {result.error}"
                print(f"{status} | 字数: {result.word_count}")
            except Exception as e:
                print(f"异常: {str(e)}")
                results.append(self._create_error_result(url, str(e)))
        return results
    
    def _extract_platform_from_url(self, url: str) -> str:
        """
        从 URL 提取平台名称
        
        Args:
            url: 网址
            
        Returns:
            str: 平台名称
        """
        platform_map = {
            'zhihu.com': '知乎',
            'juejin.cn': '掘金',
            'csdn.net': 'CSDN',
            'jianshu.com': '简书',
            'cnblogs.com': '博客园',
            'oschina.net': '开源中国',
            'infoq.cn': 'InfoQ',
            'toutiao.com': '今日头条',
            'weixin.qq.com': '微信公众号',
            'stackoverflow.com': 'Stack Overflow',
        }
        
        for domain, name in platform_map.items():
            if domain in url.lower():
                return name
        
        # 如果没有匹配，尝试提取域名
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '').split('.')[0].title()
        except:
            return '未知平台'
    
    def _get_platform_logo(self, url: str) -> str:
        """
        获取平台 Logo URL
        
        Args:
            url: 网址
            
        Returns:
            str: Logo URL
        """
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            # 使用 Google Favicon 服务
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
        except:
            return ""
    
    def _create_error_result(self, url: str, error: str) -> ExtractedContent:
        """
        创建错误结果对象
        
        Args:
            url: 网址
            error: 错误信息
            
        Returns:
            ExtractedContent: 错误结果对象
        """
        return ExtractedContent(
            url=url,
            title="",
            content="",
            platform=self._extract_platform_from_url(url),
            platform_logo=self._get_platform_logo(url),
            success=False,
            error=error
        )
    
    def __str__(self):
        return f"{self.name}(timeout={self.timeout}s)"