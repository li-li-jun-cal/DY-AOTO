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
    menu = """
请选择测试模式：

【1】关键词搜索模式
    - 搜索指定关键词的视频并采集评论
    - 适合批量采集热门内容

【2】指定视频详情模式
    - 采集指定视频ID/URL的评论
    - 适合精准采集特定视频

【3】创作者主页模式
    - 采集指定创作者的所有视频评论
    - 适合追踪特定博主

【4】查看当前配置
    - 显示当前的爬虫配置

【0】退出

请输入选项 [0-4]: """
    return input(menu).strip()


def show_config():
    """显示当前配置"""
    print("\n" + "="*60)
    print("当前配置信息:")
    print("="*60)
    print(f"平台: 抖音 (Douyin)")
    print(f"登录方式: {config.LOGIN_TYPE}")
    print(f"爬取类型: {config.CRAWLER_TYPE}")
    print(f"关键词: {config.KEYWORDS}")
    print(f"起始页码: {config.START_PAGE}")
    print(f"最大视频数: {config.CRAWLER_MAX_NOTES_COUNT}")
    print(f"最大评论数(单视频): {config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES}")
    print(f"是否爬取评论: {config.ENABLE_GET_COMMENTS}")
    print(f"是否爬取二级评论: {config.ENABLE_GET_SUB_COMMENTS}")
    print(f"数据保存方式: {config.SAVE_DATA_OPTION}")
    print(f"无头模式: {config.HEADLESS}")
    print(f"搜索排序: {['综合', '最多点赞', '最新发布'][config.SEARCH_SORT_TYPE]}")
    print("="*60 + "\n")


async def run_search_mode():
    """运行关键词搜索模式"""
    print("\n【关键词搜索模式】")
    print("-" * 60)

    keywords = input("请输入搜索关键词 (多个用逗号分隔，默认:玩具): ").strip()
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
    print("-" * 60)

    crawler = DouYinCrawler()
    await crawler.start()


async def run_detail_mode():
    """运行指定视频详情模式"""
    print("\n【指定视频详情模式】")
    print("-" * 60)
    print("支持的视频ID/URL格式:")
    print("1. 完整视频URL: https://www.douyin.com/video/7525538910311632128")
    print("2. 短链接: https://v.douyin.com/drIPtQ_WPWY/")
    print("3. 纯视频ID: 7525538910311632128")
    print("-" * 60)

    video_ids = input("请输入视频ID或URL (多个用逗号分隔): ").strip()
    if not video_ids:
        print("❌ 未输入视频ID，返回主菜单")
        return

    # 更新配置中的视频列表
    id_list = [vid.strip() for vid in video_ids.split(',')]
    config.DY_SPECIFIED_ID_LIST = id_list
    config.CRAWLER_TYPE = "detail"

    print(f"\n将采集 {len(id_list)} 个视频的评论")
    print("-" * 60)

    crawler = DouYinCrawler()
    await crawler.start()


async def run_creator_mode():
    """运行创作者主页模式"""
    print("\n【创作者主页模式】")
    print("-" * 60)
    print("支持的创作者ID/URL格式:")
    print("1. 完整主页URL: https://www.douyin.com/user/MS4wLjABAAAA...")
    print("2. sec_user_id: MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE")
    print("-" * 60)

    creator_ids = input("请输入创作者ID或URL (多个用逗号分隔): ").strip()
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
    print("-" * 60)

    crawler = DouYinCrawler()
    await crawler.start()


async def main():
    """主函数"""
    print_banner()

    while True:
        try:
            choice = print_menu()

            if choice == "0":
                print("\n👋 感谢使用，再见！")
                break

            elif choice == "1":
                await run_search_mode()
                print("\n✅ 搜索模式执行完成！")
                input("\n按回车键返回主菜单...")

            elif choice == "2":
                await run_detail_mode()
                print("\n✅ 视频详情模式执行完成！")
                input("\n按回车键返回主菜单...")

            elif choice == "3":
                await run_creator_mode()
                print("\n✅ 创作者模式执行完成！")
                input("\n按回车键返回主菜单...")

            elif choice == "4":
                show_config()
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
