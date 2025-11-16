#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音自动回复评论工具 - 定位评论回复版

功能：
1. 读取采集到的评论数据
2. 在视频页面中定位到特定评论
3. 回复该评论

⚠️ 重要警告：
- 自动评论可能违反抖音服务条款
- 可能导致账号被限制或封禁
- 请谨慎使用，建议使用小号测试
- 严格控制回复频率和数量
"""

import asyncio
import csv
import random
import os
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, BrowserContext
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))
import config


class AutoReplyComments:
    """自动回复评论类"""

    def __init__(self):
        self.browser_context = None
        self.page = None

    async def init_browser(self):
        """初始化浏览器"""
        print("🔄 正在启动浏览器...")
        playwright = await async_playwright().start()
        chromium = playwright.chromium

        # 使用与登录相同的用户数据目录
        user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)

        if not os.path.exists(user_data_dir):
            print("❌ 未找到登录数据！请先运行 python run_douyin.py 并完成登录")
            return False

        self.browser_context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # 显示浏览器便于观察
            viewport={"width": 1920, "height": 1080},
        )

        self.page = await self.browser_context.new_page()
        print("✅ 浏览器启动成功")
        return True

    def read_comments_from_csv(self, csv_file: str) -> List[Dict]:
        """从CSV文件读取评论数据"""
        comments = []

        if not os.path.exists(csv_file):
            print(f"❌ 文件不存在: {csv_file}")
            return comments

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                comments.append(row)

        print(f"✅ 从 {csv_file} 读取了 {len(comments)} 条评论")
        return comments

    def filter_comments(self, comments: List[Dict], keywords: List[str] = None) -> List[Dict]:
        """筛选评论"""
        if not keywords:
            return comments

        filtered = []
        for comment in comments:
            content = comment.get('content', '') or comment.get('评论内容', '')
            # 检查是否包含任何关键词
            if any(keyword in content for keyword in keywords):
                filtered.append(comment)

        print(f"✅ 筛选后剩余 {len(filtered)} 条评论")
        return filtered

    async def scroll_and_find_comment(self, comment_content: str, max_scrolls: int = 200) -> bool:
        """滚动页面查找特定评论 - 支持大量评论的懒加载"""
        print(f"🔍 开始查找评论: {comment_content[:30]}...")

        # 等待评论区加载
        await asyncio.sleep(3)

        last_comment_count = 0
        no_new_comments_count = 0  # 连续没有新评论的次数
        found_any_comments = False

        for scroll_count in range(max_scrolls):
            # 获取当前所有评论文本
            # 使用多个可能的选择器
            comment_selectors = [
                '[data-e2e="comment-item"]',
                '.comment-item',
                '[class*="comment"]',
                'div[role="article"]'
            ]

            current_comment_count = 0

            for selector in comment_selectors:
                try:
                    comment_elements = await self.page.query_selector_all(selector)
                    if comment_elements:
                        current_comment_count = len(comment_elements)
                        found_any_comments = True

                        # 每10次滚动显示一次进度
                        if scroll_count % 10 == 0 or scroll_count < 5:
                            print(f"  滚动第 {scroll_count + 1} 次，当前加载了 {current_comment_count} 条评论")

                        for element in comment_elements:
                            text = await element.inner_text()
                            # 检查评论内容是否匹配
                            if comment_content in text:
                                print(f"✅ 找到目标评论！（第 {scroll_count + 1} 次滚动）")
                                # 滚动到该评论
                                await element.scroll_into_view_if_needed()
                                await asyncio.sleep(1)
                                return element
                        break  # 找到了评论元素，不再尝试其他选择器
                except Exception as e:
                    continue

            # 检查是否还在加载新评论
            if current_comment_count == last_comment_count and found_any_comments:
                no_new_comments_count += 1
                if no_new_comments_count >= 10:  # 增加到10次，更保险
                    print(f"⚠️  连续10次滚动没有加载新评论，已到达评论底部")
                    print(f"  总共加载了 {current_comment_count} 条评论，未找到目标评论")
                    break
            elif current_comment_count > last_comment_count:
                no_new_comments_count = 0  # 重置计数器
                last_comment_count = current_comment_count

            # 滚动页面 - 滚动到底部触发懒加载
            # 方法1: 滚动固定距离
            await self.page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1.5)  # 增加等待时间，让抖音有时间加载

            # 方法2: 每隔3次滚动，直接滚动到页面底部（更激进）
            if scroll_count % 3 == 2:
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

        print(f"⚠️  滚动结束，未找到目标评论")
        return None

    async def find_and_click_reply_button(self, comment_element) -> bool:
        """在评论元素中查找并点击回复按钮"""
        try:
            # 尝试多个可能的回复按钮选择器
            reply_selectors = [
                'button:has-text("回复")',
                '[data-e2e="comment-reply"]',
                '.reply-button',
                'span:has-text("回复")',
                'a:has-text("回复")',
            ]

            for selector in reply_selectors:
                try:
                    reply_button = await comment_element.query_selector(selector)
                    if reply_button:
                        print(f"  找到回复按钮（选择器: {selector}）")
                        await reply_button.click()
                        # 增加等待时间，让输入框有时间加载出来
                        print("  ⏳ 等待输入框加载...")
                        await asyncio.sleep(3)
                        return True
                except:
                    continue

            print("  ⚠️  未找到回复按钮，尝试直接点击评论元素")
            # 有些网站点击评论本身就能弹出回复框
            await comment_element.click()
            await asyncio.sleep(3)
            return True

        except Exception as e:
            print(f"  ❌ 查找回复按钮失败: {e}")
            return False

    async def type_and_send_reply(self, reply_text: str) -> bool:
        """输入并发送回复"""
        try:
            # 查找回复输入框（抖音使用 contenteditable div）
            print("  🔍 正在查找输入框...")
            input_selectors = [
                'div[contenteditable="true"]',  # 抖音专用
                'textarea[placeholder*="回复"]',  # 备用
                'textarea[placeholder*="评论"]',  # 备用
                'textarea',  # 备用
            ]

            input_box = None
            for selector in input_selectors:
                try:
                    input_box = await self.page.wait_for_selector(selector, timeout=3000)
                    if input_box and await input_box.is_visible():
                        print(f"  ✅ 找到输入框")
                        break
                    else:
                        input_box = None
                except:
                    continue

            if not input_box:
                print("  ❌ 未找到输入框")
                print("  💡 调试信息：尝试截图查看页面状态...")
                # 截图帮助调试
                await self.page.screenshot(path="debug_no_input.png")
                print("  💾 已保存截图到 debug_no_input.png")
                return False

            # 点击输入框
            await input_box.click()
            await asyncio.sleep(0.5)

            # 清空输入框（防止有旧内容）
            await input_box.fill('')

            # 模拟人工逐字输入
            print(f"  ✍️  输入回复: {reply_text}")
            for char in reply_text:
                await input_box.type(char, delay=random.randint(50, 150))

            await asyncio.sleep(1)

            # 查找发送按钮（抖音用"回复"按钮）
            send_selectors = [
                'button:has-text("回复")',  # 抖音专用
                'button:has-text("发布")',  # 备用
                'button:has-text("发送")',  # 备用
            ]

            send_button = None
            for selector in send_selectors:
                try:
                    send_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if send_button:
                        print(f"  找到发送按钮（选择器: {selector}）")
                        break
                except:
                    continue

            if not send_button:
                print("  ⚠️  未找到发送按钮，可能需要按Enter键")
                # 尝试按Enter键发送
                await input_box.press('Enter')
                print("  ⏎ 已按Enter键发送")
                await asyncio.sleep(2)
                return True

            # 等待用户确认（安全机制）
            print("\n  ⚠️  准备发送回复...")
            print("  ⚠️  如需取消，请在3秒内按 Ctrl+C")
            await asyncio.sleep(3)

            # 点击发送
            await send_button.click()
            print("  ✅ 回复已发送！")
            await asyncio.sleep(2)

            return True

        except Exception as e:
            print(f"  ❌ 输入/发送失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def reply_to_comment(self, video_url: str, comment_content: str, reply_text: str, max_scrolls: int = 200) -> bool:
        """回复指定评论的完整流程

        Args:
            video_url: 视频链接
            comment_content: 要查找的评论内容
            reply_text: 回复内容
            max_scrolls: 最大滚动次数（默认200，约能加载1000条评论）
                        - 100次：约500条评论，耗时5分钟
                        - 200次：约1000条评论，耗时10分钟
                        - 500次：约2500条评论，耗时25分钟
                        - 1000次：约5000条评论，耗时50分钟
        """
        try:
            # 1. 访问视频页面
            print(f"\n📍 访问视频: {video_url}")
            # 使用 domcontentloaded 而不是 networkidle，避免超时
            # 抖音页面有很多持续的网络请求，networkidle 可能永远达不到
            await self.page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(random.uniform(3, 5))

            # 2. 滚动到评论区（模拟用户行为）
            print("⏬ 滚动到评论区...")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            await asyncio.sleep(2)

            # 3. 查找目标评论
            comment_element = await self.scroll_and_find_comment(comment_content, max_scrolls=max_scrolls)
            if not comment_element:
                print("❌ 未找到目标评论")
                return False

            # 4. 点击回复按钮
            print("🖱️  点击回复按钮...")
            if not await self.find_and_click_reply_button(comment_element):
                print("❌ 无法点击回复按钮")
                return False

            # 5. 输入并发送回复
            if not await self.type_and_send_reply(reply_text):
                print("❌ 发送回复失败")
                return False

            print("✅ 成功回复评论！")
            return True

        except Exception as e:
            print(f"❌ 回复失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def auto_reply_batch(self, comments: List[Dict], reply_templates: List[str], max_count: int = 10, max_scrolls: int = 200):
        """批量自动回复评论

        Args:
            comments: 评论列表
            reply_templates: 回复模板列表
            max_count: 最多回复多少条
            max_scrolls: 每个视频最大滚动次数（默认200）
        """
        print(f"\n🚀 开始批量回复 (最多 {max_count} 条)")
        print(f"📝 回复模板: {reply_templates}")
        print(f"🔍 滚动深度: {max_scrolls} 次（约 {max_scrolls * 5} 条评论）")
        print("-" * 60)

        success_count = 0

        for i, comment in enumerate(comments[:max_count]):
            print(f"\n{'=' * 60}")
            print(f"[{i+1}/{min(len(comments), max_count)}]")
            print(f"{'=' * 60}")

            # 获取评论信息
            video_url = comment.get('video_url') or comment.get('视频链接', '')
            comment_content = comment.get('content') or comment.get('评论内容', '')
            nickname = comment.get('nickname') or comment.get('用户昵称', '')

            if not video_url:
                print("⚠️  跳过：缺少视频URL")
                continue

            if not comment_content:
                print("⚠️  跳过：缺少评论内容")
                continue

            print(f"📖 原评论作者: {nickname}")
            print(f"📖 原评论内容: {comment_content[:100]}...")
            print(f"🔗 视频链接: {video_url}")

            # 随机选择一个回复模板
            reply_text = random.choice(reply_templates)
            print(f"💬 将回复: {reply_text}")

            # 执行回复
            success = await self.reply_to_comment(video_url, comment_content, reply_text, max_scrolls=max_scrolls)

            if success:
                success_count += 1
                print(f"✅ [{i+1}] 回复成功")
            else:
                print(f"❌ [{i+1}] 回复失败")

            # 随机延迟（30-60秒）避免被检测
            if i < min(len(comments), max_count) - 1:
                delay = random.randint(30, 60)
                print(f"\n⏰ 等待 {delay} 秒后继续...")
                for remaining in range(delay, 0, -5):
                    print(f"   剩余 {remaining} 秒...", end='\r')
                    await asyncio.sleep(5)
                print()

        print("\n" + "=" * 60)
        print(f"✅ 批量回复完成！成功: {success_count}/{min(len(comments), max_count)}")
        print("=" * 60)

    async def close(self):
        """关闭浏览器"""
        if self.browser_context:
            await self.browser_context.close()


async def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           抖音自动回复评论工具 - 定位回复版              ║
║                                                           ║
║  功能：定位到特定评论并回复                              ║
║                                                           ║
║  ⚠️  警告：                                              ║
║  - 自动评论可能违反抖音服务条款                          ║
║  - 可能导致账号被限制或封禁                              ║
║  - 请谨慎使用，建议使用小号测试                          ║
║  - 严格控制回复频率（建议每条间隔30-60秒）              ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # 确认使用
    confirm = input("\n⚠️  您确定要继续吗？ [yes/no] (默认:no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    # 初始化
    tool = AutoReplyComments()

    if not await tool.init_browser():
        return

    try:
        # 步骤1: 选择评论数据文件
        print("\n" + "=" * 60)
        print("步骤1: 选择评论数据文件")
        print("=" * 60)

        # 查找data目录下的CSV文件
        data_dir = "data/douyin/csv"
        if os.path.exists(data_dir):
            # 支持中英文文件名：_comments.csv 或 _评论.csv
            csv_files = [f for f in os.listdir(data_dir)
                        if f.endswith('_comments.csv') or f.endswith('_评论.csv')]
            if csv_files:
                print("\n可用的评论文件：")
                for i, file in enumerate(csv_files):
                    print(f"  {i+1}. {file}")

                choice = input(f"\n请选择文件 [1-{len(csv_files)}]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(csv_files):
                    csv_file = os.path.join(data_dir, csv_files[int(choice)-1])
                else:
                    print("❌ 无效选择")
                    return
            else:
                print("❌ 未找到评论文件")
                return
        else:
            csv_file = input("\n请输入评论CSV文件路径: ").strip()

        # 步骤2: 读取评论
        comments = tool.read_comments_from_csv(csv_file)
        if not comments:
            return

        # 步骤3: 筛选评论（可选）
        print("\n" + "=" * 60)
        print("步骤2: 筛选评论（可选）")
        print("=" * 60)

        use_filter = input("\n是否筛选评论？[y/n] (默认:n): ").strip().lower()

        if use_filter == 'y':
            keywords_input = input("请输入关键词（多个用逗号分隔，如：好用,推荐）: ").strip()
            if keywords_input:
                keywords = [k.strip() for k in keywords_input.split(',')]
                comments = tool.filter_comments(comments, keywords)

        if not comments:
            print("❌ 没有符合条件的评论")
            return

        # 步骤4: 设置回复内容
        print("\n" + "=" * 60)
        print("步骤3: 设置回复内容")
        print("=" * 60)

        print("\n请输入回复模板（每行一个，输入空行结束）：")
        print("示例：")
        print("  正巧我也有")
        print("  我家也有哦")
        print("  同款！")
        print()

        reply_templates = []
        while True:
            template = input(f"模板{len(reply_templates)+1}: ").strip()
            if not template:
                break
            reply_templates.append(template)

        if not reply_templates:
            print("❌ 未设置回复模板")
            return

        # 步骤5: 设置回复数量
        print("\n" + "=" * 60)
        print("步骤4: 设置回复数量")
        print("=" * 60)

        max_count_input = input(f"\n最多回复多少条评论？ (默认:5, 建议不超过10): ").strip()
        max_count = int(max_count_input) if max_count_input.isdigit() else 5

        # 步骤6: 设置滚动深度
        print("\n" + "=" * 60)
        print("步骤5: 设置滚动深度（高级选项）")
        print("=" * 60)
        print("\n滚动深度决定了能找到多靠后的评论：")
        print("  1. 快速模式（100次） - 约500条评论，5分钟")
        print("  2. 标准模式（200次） - 约1000条评论，10分钟 [推荐]")
        print("  3. 深度模式（500次） - 约2500条评论，25分钟")
        print("  4. 极限模式（1000次）- 约5000条评论，50分钟")
        print("  5. 自定义")

        scroll_mode = input("\n请选择模式 [1-5] (默认:2): ").strip()

        scroll_mapping = {
            '1': 100,
            '2': 200,
            '3': 500,
            '4': 1000,
        }

        if scroll_mode == '5':
            custom_scroll = input("请输入自定义滚动次数（1-2000）: ").strip()
            max_scrolls = int(custom_scroll) if custom_scroll.isdigit() else 200
            max_scrolls = min(max(max_scrolls, 1), 2000)  # 限制范围 1-2000
        else:
            max_scrolls = scroll_mapping.get(scroll_mode, 200)

        print(f"\n✅ 将使用 {max_scrolls} 次滚动（约能找到前 {max_scrolls * 5} 条评论）")

        # 最终确认
        print("\n" + "=" * 60)
        print("确认信息")
        print("=" * 60)
        print(f"评论总数: {len(comments)}")
        print(f"将回复: {min(len(comments), max_count)} 条")
        print(f"回复模板: {reply_templates}")
        print(f"预计耗时: {min(len(comments), max_count) * 0.75} 分钟（每条约45秒）")
        print("\n⚠️  重要提示：")
        print("  - 程序会在浏览器中自动操作")
        print("  - 你可以随时观察执行过程")
        print("  - 每条回复前有3秒确认时间")
        print("  - 按 Ctrl+C 可随时中断")
        print("-" * 60)

        final_confirm = input("\n确认开始批量回复？ [yes/no] (默认:no): ").strip().lower()
        if final_confirm != 'yes':
            print("已取消")
            return

        # 执行批量回复
        await tool.auto_reply_batch(comments, reply_templates, max_count, max_scrolls)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tool.close()


if __name__ == "__main__":
    asyncio.run(main())
