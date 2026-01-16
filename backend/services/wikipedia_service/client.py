"""Wikipedia API 客户端"""

import time
import logging
from typing import Optional, List
import wikipedia
import wikipedia.exceptions

from .models import (
    WikipediaSearchResult, 
    WikipediaPageResult, 
    WikipediaSearchResponse,
    WikipediaPageLinksResult,
    WikipediaPageCategoriesResult,
    WikipediaPageImagesResult,
    WikipediaPageReferencesResult,
    WikipediaFeaturedArticleResult
)

logger = logging.getLogger(__name__)


class WikipediaServiceError(Exception):
    """Wikipedia 服务错误"""
    pass


class WikipediaService:
    """Wikipedia API 服务（无需 API key）"""
    
    def __init__(self, language: str = "zh"):
        """
        初始化 Wikipedia 服务
        
        Args:
            language: 语言代码（默认 'zh' 中文，'en' 英文等）
        """
        self.language = language
        wikipedia.set_lang(language)
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None
    ) -> WikipediaSearchResponse:
        """
        搜索 Wikipedia 页面
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量（默认 10）
            language: 语言代码（可选，如果提供会临时切换语言）
            
        Returns:
            WikipediaSearchResponse: 搜索结果
            
        Raises:
            WikipediaServiceError: 搜索失败时抛出
        """
        start_time = time.time()
        
        try:
            # 如果指定了语言，临时切换
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            # 执行搜索（添加错误处理）
            try:
                search_results = wikipedia.search(query, results=num_results)
            except Exception as e:
                # 如果是 JSON 解析错误，可能是网络问题或 API 限制
                error_msg = str(e)
                if "JSON" in error_msg or "Expecting value" in error_msg:
                    raise WikipediaServiceError(
                        f"Wikipedia API 返回无效响应。可能是网络问题或 API 限制。"
                        f"请稍后重试或尝试其他搜索词。原始错误: {error_msg}"
                    )
                else:
                    raise WikipediaServiceError(f"搜索失败: {error_msg}")
            
            results = []
            for title in search_results:
                try:
                    # 获取页面 URL
                    page = wikipedia.page(title, auto_suggest=False)
                    url = page.url if hasattr(page, 'url') else None
                    page_id = None
                    try:
                        page_id = page.pageid if hasattr(page, 'pageid') else None
                    except:
                        pass
                    
                    results.append(WikipediaSearchResult(
                        title=title,
                        page_id=page_id,
                        snippet=None,  # wikipedia 库不直接提供 snippet
                        url=url
                    ))
                except wikipedia.exceptions.PageError:
                    # 页面不存在，跳过
                    continue
                except wikipedia.exceptions.DisambiguationError as e:
                    # 消歧义页面，使用第一个选项
                    if e.options:
                        try:
                            page = wikipedia.page(e.options[0], auto_suggest=False)
                            url = page.url if hasattr(page, 'url') else None
                            results.append(WikipediaSearchResult(
                                title=e.options[0],
                                page_id=None,
                                snippet=None,
                                url=url
                            ))
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"处理搜索结果 '{title}' 时出错: {e}")
                    continue
            
            # 恢复语言设置
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            search_time = time.time() - start_time
            
            return WikipediaSearchResponse(
                results=results,
                total_results=len(search_results),
                search_time=search_time,
                query=query,
                language=current_lang
            )
            
        except Exception as e:
            logger.error(f"Wikipedia 搜索失败: {e}", exc_info=True)
            # 恢复语言设置
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"搜索失败: {str(e)}")
    
    def get_page(
        self,
        title: str,
        language: Optional[str] = None,
        summary_only: bool = True
    ) -> WikipediaPageResult:
        """
        获取 Wikipedia 页面内容
        
        Args:
            title: 页面标题
            language: 语言代码（可选）
            summary_only: 是否只返回摘要（默认 True，节省资源）
            
        Returns:
            WikipediaPageResult: 页面内容
            
        Raises:
            WikipediaServiceError: 获取失败时抛出
        """
        try:
            # 如果指定了语言，临时切换
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            # 获取页面（添加错误处理）
            try:
                page = wikipedia.page(title, auto_suggest=False)
            except wikipedia.exceptions.DisambiguationError as e:
                # 如果是消歧义页面，使用第一个选项
                if e.options:
                    page = wikipedia.page(e.options[0], auto_suggest=False)
                else:
                    raise WikipediaServiceError(f"页面 '{title}' 存在歧义，无法确定具体页面")
            except wikipedia.exceptions.PageError:
                raise WikipediaServiceError(f"页面不存在: {title}")
            except Exception as e:
                # 处理其他异常（如 JSON 解析错误）
                error_msg = str(e)
                if "JSON" in error_msg or "Expecting value" in error_msg:
                    raise WikipediaServiceError(
                        f"Wikipedia API 返回无效响应。可能是网络问题或 API 限制。"
                        f"请稍后重试。原始错误: {error_msg}"
                    )
                else:
                    raise
            
            # 获取摘要
            summary = page.summary if hasattr(page, 'summary') else ""
            
            # 获取完整内容（如果需要）
            content = None
            if not summary_only:
                content = page.content if hasattr(page, 'content') else None
            
            # 构建 URL
            url = page.url if hasattr(page, 'url') else None
            
            # 获取页面 ID
            page_id = None
            try:
                page_id = page.pageid if hasattr(page, 'pageid') else None
            except:
                pass
            
            # 恢复语言设置
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            return WikipediaPageResult(
                title=page.title,
                page_id=page_id,
                summary=summary,
                content=content,
                url=url,
                language=current_lang
            )
            
        except WikipediaServiceError:
            # 恢复语言设置
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise
        except Exception as e:
            logger.error(f"获取 Wikipedia 页面失败: {e}", exc_info=True)
            # 恢复语言设置
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取页面失败: {str(e)}")
    
    def get_page_links(
        self,
        title: str,
        language: Optional[str] = None,
        limit: Optional[int] = None
    ) -> WikipediaPageLinksResult:
        """
        获取页面的所有链接
        
        Args:
            title: 页面标题
            language: 语言代码（可选）
            limit: 限制返回的链接数量（可选，默认返回所有）
            
        Returns:
            WikipediaPageLinksResult: 页面链接结果
        """
        try:
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            page = wikipedia.page(title, auto_suggest=False)
            links = list(page.links) if hasattr(page, 'links') else []
            
            if limit:
                links = links[:limit]
            
            url = page.url if hasattr(page, 'url') else None
            
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            return WikipediaPageLinksResult(
                title=page.title,
                url=url,
                links=links,
                links_count=len(links),
                language=current_lang
            )
        except Exception as e:
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取页面链接失败: {str(e)}")
    
    def get_page_categories(
        self,
        title: str,
        language: Optional[str] = None
    ) -> WikipediaPageCategoriesResult:
        """
        获取页面的分类
        
        Args:
            title: 页面标题
            language: 语言代码（可选）
            
        Returns:
            WikipediaPageCategoriesResult: 页面分类结果
        """
        try:
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            page = wikipedia.page(title, auto_suggest=False)
            categories = list(page.categories) if hasattr(page, 'categories') else []
            
            url = page.url if hasattr(page, 'url') else None
            
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            return WikipediaPageCategoriesResult(
                title=page.title,
                url=url,
                categories=categories,
                categories_count=len(categories),
                language=current_lang
            )
        except Exception as e:
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取页面分类失败: {str(e)}")
    
    def get_page_images(
        self,
        title: str,
        language: Optional[str] = None,
        limit: Optional[int] = None
    ) -> WikipediaPageImagesResult:
        """
        获取页面的图片列表
        
        Args:
            title: 页面标题
            language: 语言代码（可选）
            limit: 限制返回的图片数量（可选，默认返回所有）
            
        Returns:
            WikipediaPageImagesResult: 页面图片结果
        """
        try:
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            page = wikipedia.page(title, auto_suggest=False)
            images = list(page.images) if hasattr(page, 'images') else []
            
            if limit:
                images = images[:limit]
            
            url = page.url if hasattr(page, 'url') else None
            
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            return WikipediaPageImagesResult(
                title=page.title,
                url=url,
                images=images,
                images_count=len(images),
                language=current_lang
            )
        except Exception as e:
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取页面图片失败: {str(e)}")
    
    def get_page_references(
        self,
        title: str,
        language: Optional[str] = None,
        limit: Optional[int] = None
    ) -> WikipediaPageReferencesResult:
        """
        获取页面的引用/参考文献
        
        Args:
            title: 页面标题
            language: 语言代码（可选）
            limit: 限制返回的引用数量（可选，默认返回所有）
            
        Returns:
            WikipediaPageReferencesResult: 页面引用结果
        """
        try:
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            page = wikipedia.page(title, auto_suggest=False)
            references = list(page.references) if hasattr(page, 'references') else []
            
            if limit:
                references = references[:limit]
            
            url = page.url if hasattr(page, 'url') else None
            
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            return WikipediaPageReferencesResult(
                title=page.title,
                url=url,
                references=references,
                references_count=len(references),
                language=current_lang
            )
        except Exception as e:
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取页面引用失败: {str(e)}")
    
    def get_related_pages(
        self,
        title: str,
        language: Optional[str] = None,
        limit: int = 10
    ) -> WikipediaSearchResponse:
        """
        获取相关页面（通过页面的链接）
        
        Args:
            title: 页面标题
            language: 语言代码（可选）
            limit: 返回的相关页面数量（默认 10）
            
        Returns:
            WikipediaSearchResponse: 相关页面列表
        """
        try:
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            page = wikipedia.page(title, auto_suggest=False)
            links = list(page.links) if hasattr(page, 'links') else []
            
            # 限制数量
            links = links[:limit]
            
            results = []
            for link_title in links:
                try:
                    link_page = wikipedia.page(link_title, auto_suggest=False)
                    url = link_page.url if hasattr(link_page, 'url') else None
                    page_id = link_page.pageid if hasattr(link_page, 'pageid') else None
                    
                    results.append(WikipediaSearchResult(
                        title=link_title,
                        page_id=page_id,
                        snippet=None,
                        url=url
                    ))
                except:
                    # 跳过无法获取的页面
                    continue
            
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            
            return WikipediaSearchResponse(
                results=results,
                total_results=len(results),
                search_time=0.0,
                query=f"related to {title}",
                language=current_lang
            )
        except Exception as e:
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取相关页面失败: {str(e)}")
    
    def get_featured_article(
        self,
        language: Optional[str] = None
    ) -> WikipediaFeaturedArticleResult:
        """
        获取今日特色文章
        
        Args:
            language: 语言代码（可选）
            
        Returns:
            WikipediaFeaturedArticleResult: 特色文章结果
        """
        try:
            if language and language != self.language:
                wikipedia.set_lang(language)
                current_lang = language
            else:
                current_lang = self.language
            
            # Wikipedia 库没有直接获取特色文章的方法
            # 我们可以尝试搜索"特色条目"或使用特定页面
            # 这里我们返回一个提示，说明需要手动指定
            # 或者可以搜索特定页面如"Wikipedia:特色条目"
            
            # 尝试获取特色条目页面
            try:
                # 不同语言的特色条目页面名称不同
                featured_pages = {
                    'zh': 'Wikipedia:特色条目',
                    'en': 'Wikipedia:Featured articles',
                    'ja': 'Wikipedia:秀逸な記事',
                }
                
                featured_title = featured_pages.get(current_lang, 'Wikipedia:Featured articles')
                page = wikipedia.page(featured_title, auto_suggest=False)
                
                summary = page.summary if hasattr(page, 'summary') else ""
                url = page.url if hasattr(page, 'url') else None
                
                if language and language != self.language:
                    wikipedia.set_lang(self.language)
                
                return WikipediaFeaturedArticleResult(
                    title=page.title,
                    url=url,
                    summary=summary,
                    language=current_lang
                )
            except:
                # 如果无法获取特色条目页面，返回错误
                if language and language != self.language:
                    wikipedia.set_lang(self.language)
                raise WikipediaServiceError(f"无法获取 {current_lang} 语言的特色文章")
                
        except Exception as e:
            if language and language != self.language:
                wikipedia.set_lang(self.language)
            raise WikipediaServiceError(f"获取特色文章失败: {str(e)}")

