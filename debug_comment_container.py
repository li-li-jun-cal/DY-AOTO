#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评论容器诊断工具
帮助定位抖音评论区的可滚动容器
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))
import config


async def diagnose():
    """诊断评论区结构"""

    # 测试视频URL
    video_url = input("请输入要诊断的视频URL: ").strip()

    print("\n🔍 启动浏览器...")
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)

        browser_context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )

        page = await browser_context.new_page()

        print(f"📍 访问视频: {video_url}")
        await page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        print("\n" + "=" * 60)
        print("诊断报告")
        print("=" * 60)

        # 1. 查找评论元素
        comment_items = await page.query_selector_all('[data-e2e="comment-item"]')
        print(f"\n✅ 找到 {len(comment_items)} 条评论")

        # 2. 分析可滚动的div
        print("\n🔍 查找所有可滚动的div...")
        scrollable_divs = await page.evaluate("""
            () => {
                const result = [];
                const allDivs = document.querySelectorAll('div');

                for (const div of allDivs) {
                    const style = window.getComputedStyle(div);
                    const overflowY = style.overflowY;

                    if ((overflowY === 'scroll' || overflowY === 'auto') &&
                        div.scrollHeight > div.clientHeight &&
                        div.clientHeight > 100) {

                        // 检查是否包含评论
                        const hasComments = div.querySelector('[data-e2e="comment-item"]');

                        result.push({
                            className: div.className,
                            id: div.id,
                            overflowY: overflowY,
                            scrollHeight: div.scrollHeight,
                            clientHeight: div.clientHeight,
                            scrollTop: div.scrollTop,
                            hasComments: !!hasComments,
                            xpath: getXPath(div)
                        });
                    }
                }

                function getXPath(element) {
                    if (element.id) return `//*[@id="${element.id}"]`;
                    if (element === document.body) return '/html/body';

                    let ix = 0;
                    const siblings = element.parentNode.childNodes;
                    for (let i = 0; i < siblings.length; i++) {
                        const sibling = siblings[i];
                        if (sibling === element) {
                            const parent = getXPath(element.parentNode);
                            return `${parent}/${element.tagName.toLowerCase()}[${ix + 1}]`;
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }
                }

                return result;
            }
        """)

        if scrollable_divs:
            print(f"\n✅ 找到 {len(scrollable_divs)} 个可滚动div:\n")
            for i, div in enumerate(scrollable_divs):
                print(f"  [{i+1}] {'★ 包含评论!' if div['hasComments'] else ''}")
                print(f"      className: {div['className'][:50]}")
                print(f"      overflowY: {div['overflowY']}")
                print(f"      scrollHeight: {div['scrollHeight']}, clientHeight: {div['clientHeight']}")
                print(f"      scrollTop: {div['scrollTop']}")
                print(f"      xpath: {div['xpath'][:100]}...")
                print()
        else:
            print("\n❌ 未找到可滚动div!")

        # 3. 测试点击回复按钮
        print("\n🔍 测试点击第一条评论的回复按钮...")
        if comment_items:
            try:
                first_comment = comment_items[0]
                reply_btn = await first_comment.query_selector('span:has-text("回复")')
                if reply_btn:
                    print("  ✅ 找到回复按钮，点击...")
                    await reply_btn.click()
                    await asyncio.sleep(3)

                    # 查找输入框
                    print("\n🔍 查找输入框...")
                    input_info = await page.evaluate("""
                        () => {
                            const inputs = [];

                            // 查找所有可能的输入框
                            document.querySelectorAll('textarea, div[contenteditable="true"], input[type="text"]').forEach(el => {
                                const style = window.getComputedStyle(el);
                                if (style.display !== 'none' && style.visibility !== 'hidden') {
                                    inputs.push({
                                        tag: el.tagName,
                                        contenteditable: el.contentEditable,
                                        placeholder: el.placeholder || '',
                                        className: el.className,
                                        visible: el.offsetWidth > 0 && el.offsetHeight > 0
                                    });
                                }
                            });

                            return inputs;
                        }
                    """)

                    if input_info:
                        print(f"  ✅ 找到 {len(input_info)} 个输入框:\n")
                        for i, inp in enumerate(input_info):
                            print(f"    [{i+1}] {inp['tag']}")
                            print(f"        contenteditable: {inp['contenteditable']}")
                            print(f"        placeholder: {inp['placeholder']}")
                            print(f"        className: {inp['className'][:50]}")
                            print(f"        visible: {inp['visible']}")
                            print()
                    else:
                        print("  ❌ 未找到输入框!")
                else:
                    print("  ❌ 未找到回复按钮")
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")

        print("\n" + "=" * 60)
        print("诊断完成！浏览器将保持打开，请手动检查页面")
        print("按Enter键关闭...")
        print("=" * 60)

        input()
        await browser_context.close()


if __name__ == "__main__":
    asyncio.run(diagnose())
