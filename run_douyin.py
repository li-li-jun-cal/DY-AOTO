#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音爬虫启动脚本
提供简单的交互式菜单来测试抖音爬虫的各项功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

import config
from media_platform.douyin import DouYinCrawler
from database import db


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║           抖音评论采集工具 - Douyin Crawler              ║
║                   测试运行脚本                            ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_menu():
    """打印功能菜单"""
    login_type_map = {
        "qrcode": "二维码扫码",
        "phone": "手机号验证码",
        "cookie": "Cookie登录"
    }
    current_login = login_type_map.get(config.LOGIN_TYPE, "未知")

    menu = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                          主菜单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【登录配置】
  1. 配置登录方式        (当前: {current_login})
  2. 测试登录            (验证登录是否成功)

【数据采集】
  3. 关键词搜索模式      (搜索指定关键词的视频并采集评论)
  4. 指定视频详情模式    (采集指定视频ID/URL的评论)
  5. 创作者主页模式      (采集指定创作者的所有视频评论)

【配置查看】
  6. 查看当前配置        (显示所有配置信息)
  7. 修改采集参数        (修改采集数量等参数)

【其他】
  0. 退出程序

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请输入选项 [0-7]: """
    return input(menu).strip()


def configure_login():
    """配置登录方式"""
    print("\n" + "="*60)
    print("【配置登录方式】")
    print("="*60)
    print("\n抖音支持三种登录方式：")
    print("\n1. 二维码扫码登录 (推荐)")
    print("   - 最简单、最安全")
    print("   - 使用抖音APP扫码即可")
    print("   - 程序会显示二维码")

    print("\n2. 手机号验证码登录")
    print("   - 需要输入手机号")
    print("   - 需要接收验证码")
    print("   - 可能需要滑动验证码")

    print("\n3. Cookie登录")
    print("   - 适合高级用户")
    print("   - 需要手动获取Cookie")
    print("   - 有效期可能较短")

    print("\n" + "-"*60)
    choice = input("请选择登录方式 [1-3] (默认:1): ").strip()

    if choice == "2":
        config.LOGIN_TYPE = "phone"
        phone = input("请输入手机号: ").strip()
        if phone:
            print(f"✅ 已设置为手机号登录: {phone}")
            print("⚠️  注意: 登录时需要接收验证码")
        else:
            print("❌ 手机号不能为空，保持原配置")
    elif choice == "3":
        config.LOGIN_TYPE = "cookie"
        print("\n请输入Cookie (格式: key1=value1; key2=value2;...)")
        cookie = input("Cookie: ").strip()
        if cookie:
            config.COOKIES = cookie
            print("✅ 已设置为Cookie登录")
        else:
            print("❌ Cookie不能为空，保持原配置")
    else:
        config.LOGIN_TYPE = "qrcode"
        print("✅ 已设置为二维码扫码登录（推荐）")

    # 显示是否开启无头模式
    print("\n" + "-"*60)
    print("【浏览器显示设置】")
    print(f"当前无头模式: {'开启' if config.HEADLESS else '关闭'}")
    print("\n说明:")
    print("- 无头模式 = 开启: 不显示浏览器窗口")
    print("- 无头模式 = 关闭: 显示浏览器窗口（推荐首次使用）")

    headless_choice = input("\n是否开启无头模式？[y/n] (默认:n 显示浏览器): ").strip().lower()
    if headless_choice == 'y':
        config.HEADLESS = True
        print("✅ 已开启无头模式")
    else:
        config.HEADLESS = False
        print("✅ 已关闭无头模式，将显示浏览器窗口")

    print("\n" + "="*60)
    print("✅ 登录配置完成！")
    print("="*60)


async def test_login():
    """测试登录 - 只测试浏览器启动和登录，不进行数据采集"""
    print("\n" + "="*60)
    print("【测试登录】")
    print("="*60)

    login_type_map = {
        "qrcode": "二维码扫码",
        "phone": "手机号验证码",
        "cookie": "Cookie"
    }

    print(f"\n当前登录方式: {login_type_map.get(config.LOGIN_TYPE, '未知')}")
    print(f"当前无头模式: {'开启' if config.HEADLESS else '关闭'}")

    print("\n说明:")
    print("测试登录功能将只启动浏览器并执行登录流程")
    print("不会进行任何数据采集，仅验证登录是否成功")

    if config.LOGIN_TYPE == "qrcode":
        print("\n二维码登录步骤：")
        if config.HEADLESS:
            print("⚠️  警告: 无头模式下无法看到二维码！")
            print("   建议：重新配置登录方式并关闭无头模式")
            return
        print("1. 程序会打开浏览器并显示二维码")
        print("2. 使用抖音APP扫描二维码")
        print("3. 在手机上确认登录")
        print("4. 等待程序提示登录成功")
    elif config.LOGIN_TYPE == "phone":
        print("\n手机号登录步骤：")
        print("1. 程序会打开浏览器")
        print("2. 输入手机号后点击获取验证码")
        print("3. 可能需要滑动验证码")
        print("4. 输入收到的验证码")
        print("5. 等待程序提示登录成功")
    elif config.LOGIN_TYPE == "cookie":
        print("\nCookie登录步骤：")
        print("1. 程序会使用您提供的Cookie登录")
        print("2. 如果Cookie有效，将直接登录成功")
        print("3. 如果Cookie失效，需重新配置")

    print("\n" + "-"*60)
    confirm = input("是否开始测试登录？[y/n] (默认:y): ").strip().lower()

    if confirm == 'n':
        print("已取消登录测试")
        return

    print("\n开始登录测试...")
    print("-"*60)

    try:
        print("\n🔄 正在启动浏览器...")
        print("提示: 如果长时间无响应，请检查playwright是否已安装")
        print("      安装命令: playwright install chromium\n")

        from playwright.async_api import async_playwright
        from media_platform.douyin.login import DouYinLogin
        from media_platform.douyin.client import DouYinClient
        from tools import utils

        # 检查是否启用代理
        playwright_proxy_format = None
        if config.ENABLE_IP_PROXY:
            print("⚠️  检测到启用了代理，可能导致连接问题")
            print("   如果登录失败，建议关闭代理重试")
            print("   设置方法: 在config/base_config.py中设置 ENABLE_IP_PROXY = False\n")

        async with async_playwright() as playwright:
            # 启动浏览器
            chromium = playwright.chromium
            # 🔥 重要：必须使用与 crawler.start() 相同的路径！
            # crawler 使用 browser_data/dy_user_data_dir，所以这里也要一致
            import os
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=config.HEADLESS,
                proxy=playwright_proxy_format,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )

            print("✅ 浏览器启动成功")

            # 创建页面并访问抖音
            context_page = await browser_context.new_page()
            await context_page.goto("https://www.douyin.com")
            print("✅ 已访问抖音首页")

            # 创建客户端
            dy_client = DouYinClient(
                proxy=None,  # 不使用代理
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.douyin.com/",
                    "Cookie": config.COOKIES
                },
                playwright_page=context_page,
                cookie_dict={}
            )

            # 检查是否已登录
            print("\n🔍 正在检查登录状态...")
            is_logged_in = await dy_client.pong(browser_context=browser_context)

            if is_logged_in:
                print("✅ 检测到已有登录状态（使用缓存的登录信息）")
            else:
                print("ℹ️  未检测到登录状态，开始执行登录流程...\n")

                # 执行登录
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # 手机号登录时需要配置
                    browser_context=browser_context,
                    context_page=context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()

                # 更新客户端的cookies
                await dy_client.update_cookies(browser_context=browser_context)
                print("✅ 登录流程完成")

            # 再次验证登录状态
            print("\n🔍 正在验证登录状态...")
            await asyncio.sleep(2)
            is_logged_in = await dy_client.pong(browser_context=browser_context)

            if is_logged_in:
                print("\n" + "="*60)
                print("✅✅✅ 登录测试成功！✅✅✅")
                print("="*60)
                print("\n提示:")
                print(f"- 登录状态已保存到: {user_data_dir}/ 目录")
                print("- 下次运行将自动使用已保存的登录状态")
                print(f"- 如需重新登录，请删除 {user_data_dir}/ 目录")
                print("- 现在可以进行正式的数据采集了")
            else:
                print("\n" + "="*60)
                print("⚠️  登录状态验证失败")
                print("="*60)
                print("\n虽然登录流程已执行，但无法确认登录状态")
                print("建议：")
                print("1. 关闭无头模式，手动检查浏览器中的登录状态")
                print("2. 尝试其他登录方式（如二维码登录）")
                print("3. 检查Cookie是否有效（如果使用Cookie登录）")

            # 关闭浏览器
            await browser_context.close()
            print("\n🔄 浏览器已关闭")

    except Exception as e:
        print("\n" + "="*60)
        print("❌ 登录测试失败！")
        print("="*60)
        print(f"\n错误信息: {e}")
        print("\n可能的原因:")
        print("1. Playwright未安装或浏览器驱动未安装")
        print("   解决方法: playwright install chromium")
        print("2. 网络连接问题或代理配置错误")
        print("   解决方法: 关闭代理 (config.ENABLE_IP_PROXY = False)")
        print("3. 二维码已过期（请重试）")
        print("4. 验证码输入错误")
        print("5. Cookie已失效")
        print("\n调试建议:")
        print("- 关闭无头模式重试（在配置登录方式中设置）")
        print("- 检查网络连接和代理设置")
        print("- 查看下方的详细错误信息")
        print("\n详细错误:")
        import traceback
        traceback.print_exc()


def show_config():
    """显示当前配置"""
    print("\n" + "="*60)
    print("当前配置信息")
    print("="*60)

    login_type_map = {
        "qrcode": "二维码扫码",
        "phone": "手机号验证码",
        "cookie": "Cookie登录"
    }

    print("\n【登录配置】")
    print(f"  登录方式: {login_type_map.get(config.LOGIN_TYPE, '未知')}")
    print(f"  无头模式: {'开启' if config.HEADLESS else '关闭'}")
    print(f"  保存登录状态: {'是' if config.SAVE_LOGIN_STATE else '否'}")

    print("\n【基础配置】")
    print(f"  平台: 抖音 (Douyin)")
    print(f"  爬取类型: {config.CRAWLER_TYPE}")
    print(f"  搜索关键词: {config.KEYWORDS}")
    print(f"  起始页码: {config.START_PAGE}")

    print("\n【采集控制】")
    print(f"  最大视频数: {config.CRAWLER_MAX_NOTES_COUNT}")
    print(f"  最大评论数(单视频): {config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES}")
    print(f"  是否爬取评论: {'是' if config.ENABLE_GET_COMMENTS else '否'}")
    print(f"  是否爬取二级评论: {'是' if config.ENABLE_GET_SUB_COMMENTS else '否'}")
    print(f"  并发数: {config.MAX_CONCURRENCY_NUM}")

    print("\n【抖音专属配置】")
    sort_type_map = {0: "综合排序", 1: "最多点赞", 2: "最新发布"}
    print(f"  搜索排序: {sort_type_map.get(config.SEARCH_SORT_TYPE, '未知')}")

    print("\n【数据存储】")
    print(f"  保存方式: {config.SAVE_DATA_OPTION}")
    print(f"  是否爬取媒体: {'是' if config.ENABLE_GET_MEIDAS else '否'}")

    print("\n【高级选项】")
    print(f"  启用代理: {'是' if config.ENABLE_IP_PROXY else '否'}")
    print(f"  CDP模式: {'是' if config.ENABLE_CDP_MODE else '否'}")
    print(f"  RPA搜索: {'是' if config.ENABLE_RPA_SEARCH else '否'}")

    print("="*60 + "\n")


def modify_config():
    """修改采集参数"""
    print("\n" + "="*60)
    print("【修改采集参数】")
    print("="*60)

    print(f"\n当前最大视频数: {config.CRAWLER_MAX_NOTES_COUNT}")
    max_videos = input("请输入新的最大视频数 (直接回车保持不变): ").strip()
    if max_videos.isdigit():
        config.CRAWLER_MAX_NOTES_COUNT = int(max_videos)
        print(f"✅ 已设置为: {config.CRAWLER_MAX_NOTES_COUNT}")

    print(f"\n当前最大评论数(单视频): {config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES}")
    max_comments = input("请输入新的最大评论数 (直接回车保持不变): ").strip()
    if max_comments.isdigit():
        config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = int(max_comments)
        print(f"✅ 已设置为: {config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES}")

    print(f"\n当前是否爬取二级评论: {'是' if config.ENABLE_GET_SUB_COMMENTS else '否'}")
    sub_comment = input("是否爬取二级评论？[y/n] (直接回车保持不变): ").strip().lower()
    if sub_comment == 'y':
        config.ENABLE_GET_SUB_COMMENTS = True
        print("✅ 已开启二级评论采集")
    elif sub_comment == 'n':
        config.ENABLE_GET_SUB_COMMENTS = False
        print("✅ 已关闭二级评论采集")

    print("\n" + "="*60)
    print("✅ 参数修改完成！")
    print("="*60)


async def run_search_mode():
    """运行关键词搜索模式"""
    print("\n" + "="*60)
    print("【关键词搜索模式】")
    print("="*60)

    # 检查登录状态
    import os
    # 🔥 使用与 crawler 相同的路径
    user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
    has_login_cache = os.path.exists(user_data_dir)

    if not has_login_cache:
        print("\n⚠️  警告：检测到您可能还未登录！")
        print("   数据采集需要登录状态，未登录可能导致：")
        print("   - 搜索结果为空")
        print("   - 无法获取评论")
        print("   - 被限制访问")
        print("\n建议操作：")
        print("   1. 先返回主菜单")
        print("   2. 选择【1】配置登录方式")
        print("   3. 选择【2】测试登录")
        print("   4. 登录成功后再进行数据采集")
        print("-" * 60)
        confirm_continue = input("\n是否仍要继续（会自动触发登录）？[y/n] (默认:n): ").strip().lower()
        if confirm_continue != 'y':
            print("已取消，请先完成登录")
            return

    keywords = input("\n请输入搜索关键词 (多个用逗号分隔，默认:玩具): ").strip()
    if keywords:
        config.KEYWORDS = keywords

    max_videos = input(f"最多采集多少个视频 (默认:{config.CRAWLER_MAX_NOTES_COUNT}): ").strip()
    if max_videos.isdigit():
        config.CRAWLER_MAX_NOTES_COUNT = int(max_videos)

    max_comments = input(f"每个视频最多采集多少条评论 (默认:{config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES}): ").strip()
    if max_comments.isdigit():
        config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = int(max_comments)

    config.CRAWLER_TYPE = "search"

    print(f"\n开始搜索关键词: {config.KEYWORDS}")
    print(f"将采集 {config.CRAWLER_MAX_NOTES_COUNT} 个视频，每个视频最多 {config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES} 条评论")
    print(f"登录方式: {config.LOGIN_TYPE}")

    # 检查配置冲突
    if config.LOGIN_TYPE == "qrcode" and config.HEADLESS:
        print("\n⚠️  配置冲突警告：")
        print("   当前使用二维码登录 + 无头模式")
        print("   这会导致看不到二维码，登录将失败！")
        print("   建议：在 config/base_config.py 中设置 HEADLESS = False")

    print("-" * 60)

    confirm = input("\n确认开始采集？[y/n] (默认:y): ").strip().lower()
    if confirm == 'n':
        print("已取消采集")
        return

    crawler = DouYinCrawler()
    await crawler.start()


async def run_detail_mode():
    """运行指定视频详情模式"""
    print("\n" + "="*60)
    print("【指定视频详情模式】")
    print("="*60)

    # 检查登录状态
    import os
    # 🔥 使用与 crawler 相同的路径
    user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
    has_login_cache = os.path.exists(user_data_dir)

    if not has_login_cache:
        print("\n⚠️  警告：检测到您可能还未登录！")
        print("   建议先完成登录再进行数据采集")
        confirm_continue = input("\n是否仍要继续（会自动触发登录）？[y/n] (默认:n): ").strip().lower()
        if confirm_continue != 'y':
            print("已取消，请先完成登录")
            return

    print("\n支持的视频ID/URL格式:")
    print("1. 完整视频URL: https://www.douyin.com/video/7525538910311632128")
    print("2. 短链接: https://v.douyin.com/drIPtQ_WPWY/")
    print("3. 纯视频ID: 7525538910311632128")
    print("-" * 60)

    video_ids = input("\n请输入视频ID或URL (多个用逗号分隔): ").strip()
    if not video_ids:
        print("❌ 未输入视频ID，返回主菜单")
        return

    # 更新配置中的视频列表
    id_list = [vid.strip() for vid in video_ids.split(',')]
    config.DY_SPECIFIED_ID_LIST = id_list
    config.CRAWLER_TYPE = "detail"

    print(f"\n将采集 {len(id_list)} 个视频的评论")
    print(f"登录方式: {config.LOGIN_TYPE}")
    print("-" * 60)

    confirm = input("\n确认开始采集？[y/n] (默认:y): ").strip().lower()
    if confirm == 'n':
        print("已取消采集")
        return

    crawler = DouYinCrawler()
    await crawler.start()


async def run_creator_mode():
    """运行创作者主页模式"""
    print("\n" + "="*60)
    print("【创作者主页模式】")
    print("="*60)

    # 检查登录状态
    import os
    # 🔥 使用与 crawler 相同的路径
    user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
    has_login_cache = os.path.exists(user_data_dir)

    if not has_login_cache:
        print("\n⚠️  警告：检测到您可能还未登录！")
        print("   建议先完成登录再进行数据采集")
        confirm_continue = input("\n是否仍要继续（会自动触发登录）？[y/n] (默认:n): ").strip().lower()
        if confirm_continue != 'y':
            print("已取消，请先完成登录")
            return

    print("\n支持的创作者ID/URL格式:")
    print("1. 完整主页URL: https://www.douyin.com/user/MS4wLjABAAAA...")
    print("2. sec_user_id: MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE")
    print("-" * 60)

    creator_ids = input("\n请输入创作者ID或URL (多个用逗号分隔): ").strip()
    if not creator_ids:
        print("❌ 未输入创作者ID，返回主菜单")
        return

    # 更新配置中的创作者列表
    id_list = [cid.strip() for cid in creator_ids.split(',')]
    config.DY_CREATOR_ID_LIST = id_list
    config.CRAWLER_TYPE = "creator"

    max_videos = input(f"每个创作者最多采集多少个视频 (默认:{config.CRAWLER_MAX_NOTES_COUNT}): ").strip()
    if max_videos.isdigit():
        config.CRAWLER_MAX_NOTES_COUNT = int(max_videos)

    print(f"\n将采集 {len(id_list)} 个创作者的视频评论")
    print(f"每个创作者最多采集 {config.CRAWLER_MAX_NOTES_COUNT} 个视频")
    print(f"登录方式: {config.LOGIN_TYPE}")
    print("-" * 60)

    confirm = input("\n确认开始采集？[y/n] (默认:y): ").strip().lower()
    if confirm == 'n':
        print("已取消采集")
        return

    crawler = DouYinCrawler()
    await crawler.start()


async def main():
    """主函数"""
    print_banner()

    print("\n💡 使用提示:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. 首次使用请先【配置登录方式】并【测试登录】")
    print("2. 登录成功后，选择需要的采集模式进行数据采集")
    print("3. 采集的数据会保存在 data/douyin/ 目录下")
    print("4. 如遇问题，可关闭无头模式查看浏览器窗口")
    print("5. 二维码登录时必须关闭无头模式才能看到二维码")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 检查playwright是否安装
    print("\n🔍 环境检查:")
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright 已安装")
    except ImportError:
        print("❌ Playwright 未安装!")
        print("   请运行: pip install playwright")
        print("   然后运行: playwright install chromium")
        return

    while True:
        try:
            choice = print_menu()

            if choice == "0":
                print("\n👋 感谢使用，再见！")
                break

            elif choice == "1":
                configure_login()
                input("\n按回车键返回主菜单...")

            elif choice == "2":
                await test_login()
                input("\n按回车键返回主菜单...")

            elif choice == "3":
                await run_search_mode()
                print("\n✅ 搜索模式执行完成！")
                print(f"数据已保存到: data/douyin/{config.SAVE_DATA_OPTION}/")
                input("\n按回车键返回主菜单...")

            elif choice == "4":
                await run_detail_mode()
                print("\n✅ 视频详情模式执行完成！")
                print(f"数据已保存到: data/douyin/{config.SAVE_DATA_OPTION}/")
                input("\n按回车键返回主菜单...")

            elif choice == "5":
                await run_creator_mode()
                print("\n✅ 创作者模式执行完成！")
                print(f"数据已保存到: data/douyin/{config.SAVE_DATA_OPTION}/")
                input("\n按回车键返回主菜单...")

            elif choice == "6":
                show_config()
                input("按回车键返回主菜单...")

            elif choice == "7":
                modify_config()
                input("按回车键返回主菜单...")

            else:
                print("\n❌ 无效的选项，请重新输入")
                input("按回车键继续...")

        except KeyboardInterrupt:
            print("\n\n👋 检测到 Ctrl+C，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
            input("\n按回车键返回主菜单...")

    # 清理资源
    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已退出")
    except Exception as e:
        print(f"\n❌ 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
