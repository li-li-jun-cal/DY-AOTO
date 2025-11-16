# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import os
import random
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import douyin as douyin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from tools.resource_path import get_libs_path
from var import crawler_type_var, source_keyword_var

from .client import DouYinClient
from .exception import DataFetchError
from .field import PublishTimeType
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    context_page: Page
    dy_client: DouYinClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.douyin.com"
        self.cdp_manager = None
        self._is_unified_browser = False  # 🔥 标记是否为统一浏览器模式
        self.progress_callback = None  # 🔥 进度回调函数

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[DouYinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                # 🔥 不使用 stealth.min.js（包含箭头函数，会导致 SyntaxError）
                # 改用简化的反检测脚本（已在 gui_app.py 中注入）
                # stealth_js_path = get_libs_path("stealth.min.js")
                # await self.browser_context.add_init_script(path=stealth_js_path)
                pass  # 反检测脚本已在 GUI 登录时注入

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            if not await self.dy_client.pong(browser_context=self.browser_context):
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_videos()

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # douyin limit page fixed value
        # 🔥 不再强制修改用户设置的数量，严格遵守用户设置
        # if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
        #     config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        start_page = config.START_PAGE  # start page number
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []
            page = 0
            dy_search_id = ""

            # 🔥 严格限制采集数量
            max_notes_to_collect = config.CRAWLER_MAX_NOTES_COUNT
            utils.logger.info(f"[DouYinCrawler.search] 🎯 目标采集数量: {max_notes_to_collect} 个视频")

            while len(aweme_list) < max_notes_to_collect:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}, 已采集: {len(aweme_list)}/{max_notes_to_collect}")
                    # 获取排序类型配置
                    from media_platform.douyin.field import SearchSortType
                    sort_type = SearchSortType.GENERAL  # 默认综合排序
                    if hasattr(config, 'SEARCH_SORT_TYPE'):
                        if config.SEARCH_SORT_TYPE == 1:
                            sort_type = SearchSortType.MOST_LIKE  # 按最多点赞
                        elif config.SEARCH_SORT_TYPE == 2:
                            sort_type = SearchSortType.LATEST     # 按最新发布

                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * dy_limit_count - dy_limit_count,
                        sort_type=sort_type,
                        publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                        search_id=dy_search_id,
                    )
                    # 🔥 调试：打印完整响应以诊断问题
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.warning(f"[DouYinCrawler.search] ⚠️  搜索返回空结果！")
                        utils.logger.warning(f"[DouYinCrawler.search] 完整响应: {posts_res}")
                        # 检查是否有错误信息
                        if "status_code" in posts_res and posts_res["status_code"] != 0:
                            utils.logger.error(f"[DouYinCrawler.search] API返回错误码: {posts_res.get('status_code')}, 错误信息: {posts_res.get('status_msg', 'unknown')}")
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                for post_item in posts_res.get("data"):
                    # 🔥 严格检查是否已达到目标数量
                    if len(aweme_list) >= max_notes_to_collect:
                        utils.logger.info(f"[DouYinCrawler.search] ✅ 已达到目标数量 {max_notes_to_collect}，停止采集")
                        break

                    try:
                        aweme_info: Dict = (post_item.get("aweme_info") or post_item.get("aweme_mix_info", {}).get("mix_items")[0])
                    except TypeError:
                        continue
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    await douyin_store.update_douyin_aweme(aweme_item=aweme_info)
                    await self.get_aweme_media(aweme_item=aweme_info)

                    # 🔥 更新进度
                    if self.progress_callback:
                        current = len(aweme_list)
                        total = max_notes_to_collect
                        title = aweme_info.get("desc", "")[:20]
                        self.progress_callback(current, total, f"正在采集第{current}个视频: {title}...")

                # 🔥 如果已达到目标数量，退出循环
                if len(aweme_list) >= max_notes_to_collect:
                    break

                # Sleep after each page navigation
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.search] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")

            # 🔥 最终确保只采集设置的数量
            aweme_list = aweme_list[:max_notes_to_collect]
            utils.logger.info(f"[DouYinCrawler.search] ✅ 最终采集数量: {len(aweme_list)}/{max_notes_to_collect}, aweme_list:{aweme_list}")
            await self.batch_get_note_comments(aweme_list)

    async def get_specified_awemes(self):
        """Get the information and comments of the specified post from URLs or IDs"""
        utils.logger.info("[DouYinCrawler.get_specified_awemes] Parsing video URLs...")
        aweme_id_list = []
        for video_url in config.DY_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)

                # 处理短链接
                if video_info.url_type == "short":
                    utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Resolving short link: {video_url}")
                    resolved_url = await self.dy_client.resolve_short_url(video_url)
                    if resolved_url:
                        # 从解析后的URL中提取视频ID
                        video_info = parse_video_info_from_url(resolved_url)
                        utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Short link resolved to aweme ID: {video_info.aweme_id}")
                    else:
                        utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to resolve short link: {video_url}")
                        continue

                aweme_id_list.append(video_info.aweme_id)
                utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Parsed aweme ID: {video_info.aweme_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to parse video URL: {e}")
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in aweme_id_list]
        aweme_details = await asyncio.gather(*task_list)
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                await douyin_store.update_douyin_aweme(aweme_item=aweme_detail)
                await self.get_aweme_media(aweme_item=aweme_detail)

        # 🔥 传递进度回调给评论采集
        progress_callback = getattr(self, 'progress_callback', None)
        await self.batch_get_note_comments(aweme_id_list, progress_callback=progress_callback)

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get note detail"""
        async with semaphore:
            try:
                result = await self.dy_client.get_video_by_id(aweme_id)
                # Sleep after fetching aweme detail
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.get_aweme_detail] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching aweme {aweme_id}")
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str], progress_callback=None) -> None:
        """
        Batch get note comments
        Args:
            aweme_list: 视频ID列表
            progress_callback: 进度回调函数 callback(current, total, comment_count)
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        # 🔥 显示总数
        total_videos = len(aweme_list)
        utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] 开始采集 {total_videos} 个视频的评论")
        print(f"\n📊 开始采集 {total_videos} 个视频的评论\n")

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for index, aweme_id in enumerate(aweme_list, 1):
            # 🔥 显示当前进度
            print(f"🎬 [{index}/{total_videos}] 正在采集视频 {aweme_id} 的评论...")
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] [{index}/{total_videos}] 正在采集视频 {aweme_id}")

            # 🔥 调用进度回调
            if progress_callback:
                try:
                    progress_callback(index, total_videos, 0)
                except Exception as e:
                    utils.logger.warning(f"进度回调失败: {e}")

            task = asyncio.create_task(self.get_comments(aweme_id, semaphore, index, total_videos, progress_callback), name=aweme_id)
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

        print(f"\n✅ 所有 {total_videos} 个视频的评论采集完成!\n")

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore, index: int = 0, total: int = 0, progress_callback=None) -> None:
        async with semaphore:
            try:
                # 🔥 显示开始采集
                if index > 0 and total > 0:
                    print(f"   💬 [{index}/{total}] 开始获取视频 {aweme_id} 的评论...")

                # 🔥 创建评论进度回调包装器
                comment_count = [0]  # 使用列表来在闭包中修改值
                max_count = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES

                async def comment_callback(aweme_id_inner, comments):
                    # 先调用原始的存储回调
                    await douyin_store.batch_update_dy_aweme_comments(aweme_id_inner, comments)
                    # 更新评论计数
                    comment_count[0] += len(comments)
                    # 调用进度回调
                    if progress_callback:
                        try:
                            progress_callback(index, total, comment_count[0], max_count)
                        except Exception as e:
                            utils.logger.warning(f"评论进度回调失败: {e}")

                # 将关键词列表传递给 get_aweme_all_comments 方法
                # Use fixed crawling interval
                crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=comment_callback,  # 🔥 使用包装后的回调
                    max_count=max_count,
                )
                # Sleep after fetching comments
                await asyncio.sleep(crawl_interval)

                # 🔥 显示完成
                if index > 0 and total > 0:
                    print(f"   ✅ [{index}/{total}] 视频 {aweme_id} 评论采集完成 (共{comment_count[0]}条)")

                utils.logger.info(f"[DouYinCrawler.get_comments] Sleeping for {crawl_interval} seconds after fetching comments for aweme {aweme_id}")
                utils.logger.info(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")
                if index > 0 and total > 0:
                    print(f"   ❌ [{index}/{total}] 视频 {aweme_id} 评论采集失败: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator from URLs or IDs
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Parsing creator URLs...")

        for creator_url in config.DY_CREATOR_ID_LIST:
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                user_id = creator_info_parsed.sec_user_id
                utils.logger.info(f"[DouYinCrawler.get_creators_and_videos] Parsed sec_user_id: {user_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                continue

            creator_info: Dict = await self.dy_client.get_user_info(user_id)
            if creator_info:
                await douyin_store.save_creator(user_id, creator=creator_info)

            # Get all video information of the creator
            all_video_list = await self.dy_client.get_all_user_aweme_posts(sec_user_id=user_id, callback=self.fetch_creator_video_detail)

            video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
            await self.batch_get_note_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list]

        note_details = await asyncio.gather(*task_list)
        for aweme_item in note_details:
            if aweme_item is not None:
                await douyin_store.update_douyin_aweme(aweme_item=aweme_item)
                await self.get_aweme_media(aweme_item=aweme_item)

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DouYinClient:
        """Create douyin client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        # 🔥 调试：检查是否有关键Cookie
        has_sessionid = "sessionid" in cookie_dict or "sessionid_ss" in cookie_dict
        utils.logger.info(f"[DouYinCrawler.create_douyin_client] Cookie数量: {len(cookie_dict)}, 包含sessionid: {has_sessionid}")
        if not has_sessionid:
            utils.logger.warning(f"[DouYinCrawler.create_douyin_client] ⚠️  警告：未找到sessionid，可能未登录！")
        # 🔥 修复箭头函数语法 - 改用 function 语法
        user_agent = await self.context_page.evaluate("function() { return navigator.userAgent; }")
        douyin_client = DouYinClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": user_agent,
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return douyin_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # 添加反检测脚本
            await self.cdp_manager.add_stealth_script()

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[DouYinCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[DouYinCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """Close browser context"""
        # 🔥 如果是统一浏览器模式，不关闭浏览器上下文（由GUI管理）
        if self._is_unified_browser:
            utils.logger.info("[DouYinCrawler.close] 统一浏览器模式，跳过关闭浏览器上下文")
            return

        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")

    async def get_aweme_media(self, aweme_item: Dict):
        """
        获取抖音媒体，自动判断媒体类型是短视频还是帖子图片并下载

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info(f"[DouYinCrawler.get_aweme_media] Crawling image mode is not enabled")
            return
        # 笔记 urls 列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)
        # 视频 url，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)
        # TODO: 抖音并没采用音视频分离的策略，故音频可从原视频中分离，暂不提取
        if note_download_url:
            await self.get_aweme_images(aweme_item)
        else:
            await self.get_aweme_video(aweme_item)

    async def get_aweme_images(self, aweme_item: Dict):
        """
        get aweme images. please use get_aweme_media
        
        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")
        # 笔记 urls 列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)

        if not note_download_url:
            return
        picNum = 0
        for url in note_download_url:
            if not url:
                continue
            content = await self.dy_client.get_aweme_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            extension_file_name = f"{picNum:>03d}.jpeg"
            picNum += 1
            await douyin_store.update_dy_aweme_image(aweme_id, content, extension_file_name)

    async def get_aweme_video(self, aweme_item: Dict):
        """
        get aweme videos. please use get_aweme_media

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")

        # 视频 url，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)

        if not video_download_url:
            return
        content = await self.dy_client.get_aweme_media(video_download_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        extension_file_name = f"video.mp4"
        await douyin_store.update_dy_aweme_video(aweme_id, content, extension_file_name)
