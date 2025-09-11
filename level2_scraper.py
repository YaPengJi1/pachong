#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度事件评论爬虫 - 二级界面爬虫
从子事件页面提取用户评论数据，实时存储到JSON和表格文件
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Level2Scraper:
    def __init__(self, core_event_name="", output_dir: str = None, csv_output_file: str = None):
        self.session = requests.Session()
        self.driver = None
        self.comments_data = []
        self.core_event_name = core_event_name
        # 输出目录与文件
        self.output_dir = output_dir or 'data'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        self.level2_file = os.path.join(self.output_dir, 'level2_data.json')
        self.table_file = os.path.join(self.output_dir, f"{self._sanitize_filename(core_event_name)}_评论数据.xlsx")
        self.csv_output_file = csv_output_file  # 例如 D:/.../Israeli_Palestinian_conflict.csv
        self._init_session()
        self._init_selenium()
        self._ensure_data_dir()
    
    def _sanitize_filename(self, filename):
        """清理文件名，移除非法字符"""
        if not filename:
            return "未知事件"
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        # 限制长度
        if len(filename) > 50:
            filename = filename[:50]
        return filename
    
    def _init_session(self):
        """初始化requests会话"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.baidu.com/',
        })
    
    def _init_selenium(self):
        """初始化Selenium"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 优先尝试：Selenium Manager（不下载第三方依赖）
            try:
                logger.info("正在初始化Chrome（Selenium Manager）...")
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
                logger.info("Selenium WebDriver 初始化成功 (Chrome)")
                return
            except Exception as e1:
                logger.warning(f"Chrome (Selenium Manager) 初始化失败: {e1}")

            # 备用：本地chromedriver（通过环境变量指定）
            try:
                logger.info("尝试使用本地chromedriver（跳过网络下载）...")
                os.environ['WDM_LOCAL'] = '1'
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '')
                if chromedriver_path and os.path.exists(chromedriver_path):
                    logger.info(f"使用CHROMEDRIVER_PATH: {chromedriver_path}")
                    self.driver = webdriver.Chrome(service=ChromeService(chromedriver_path), options=chrome_options)
                    self.driver.set_page_load_timeout(30)
                    logger.info("Selenium WebDriver 初始化成功 (本地chromedriver)")
                    return
            except Exception as e2:
                logger.warning(f"本地chromedriver 初始化失败: {e2}")

            # 最后备用：Edge
            try:
                logger.info("尝试使用Edge WebDriver 初始化...")
                edge_options = EdgeOptions()
                edge_options.use_chromium = True
                edge_options.add_argument('--headless')
                edge_options.add_argument('--no-sandbox')
                edge_options.add_argument('--disable-dev-shm-usage')
                edge_options.add_argument('--disable-gpu')
                edge_options.add_argument('--disable-extensions')
                edge_options.add_argument('--disable-logging')
                edge_options.add_argument('--disable-web-security')
                edge_options.add_argument('--window-size=1920,1080')
                self.driver = webdriver.Edge(options=edge_options)
                self.driver.set_page_load_timeout(30)
                logger.info("Selenium WebDriver 初始化成功 (Edge)")
                return
            except Exception as e3:
                logger.error(f"Edge 初始化失败: {e3}")

            raise RuntimeError("无法初始化任何浏览器驱动。请安装 Chrome/Edge 或提供 CHROMEDRIVER_PATH。")
        except Exception as e:
            logger.error(f"Selenium WebDriver 初始化失败: {e}")
            logger.error("请确保已安装Chrome浏览器和ChromeDriver")
            self.driver = None
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists('data'):
            os.makedirs('data')
            logger.info("创建数据目录: data")
    
    def scrape_comments_from_url(self, url, event_title, event_id):
        """从单个URL爬取评论"""
        logger.info(f"开始爬取评论: {event_title[:30]}...")
        
        if not self.driver:
            logger.error("WebDriver未初始化，无法爬取")
            return []
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待页面加载
            time.sleep(3)
            
            # 滚动页面加载更多评论
            for i in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            comments = self._extract_comments(soup, event_title, event_id, url)
            
            # 实时存储每条评论
            for comment in comments:
                self._save_single_comment(comment)
            
            logger.info(f"从 {event_title[:30]}... 提取到 {len(comments)} 条评论")
            return comments
            
        except Exception as e:
            logger.error(f"爬取评论失败 {event_title[:30]}...: {e}")
            return []
    
    def _extract_comments(self, soup, event_title, event_id, url):
        """从页面中提取评论"""
        comments = []
        
        # 根据实际页面结构，评论容器是 xcp-item
        comment_containers = soup.select('div.xcp-item')
        
        if not comment_containers:
            # 备用选择器
            selectors = [
                'div[data-reply-id]',
                'div.comment-item',
                'div.comment',
                'div.user-comment',
                'div[class*="comment"]',
                'div[class*="reply"]',
                'div[class*="user"]',
                '.comment-list div',
                '.reply-list div',
                'li[class*="comment"]',
                'li[class*="reply"]',
                'div[data-role="comment"]',
                'div[data-type="comment"]'
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                if containers:
                    logger.info(f"使用选择器 '{selector}' 找到 {len(containers)} 个评论容器")
                    comment_containers.extend(containers)
        
        # 去重
        comment_containers = list(set(comment_containers))
        
        # 如果还是没找到，尝试查找包含用户信息的元素
        if not comment_containers:
            logger.info("尝试查找包含用户信息的元素...")
            user_elements = soup.find_all(['div', 'li'], string=re.compile(r'用户|网友|评论'))
            if user_elements:
                comment_containers = user_elements
                logger.info(f"找到 {len(comment_containers)} 个可能的用户元素")
        
        logger.info(f"最终找到 {len(comment_containers)} 个评论容器")
        
        for i, container in enumerate(comment_containers):
            try:
                comment = self._extract_single_comment(container, event_title, event_id, url, i+1)
                if comment:
                    comments.append(comment)
            except Exception as e:
                logger.warning(f"解析评论 {i+1} 失败: {e}")
                continue
        
        return comments
    
    def _extract_single_comment(self, container, event_title, event_id, url, comment_index):
        """从单个评论容器中提取评论信息"""
        comment = {
            'event_title': event_title,
            'event_id': event_id,
            'event_url': url,
            'comment_index': comment_index,
            'user_id': '',
            'comment_time': '',
            'comment_content': '',
            'user_location': '',
            'like_count': 0,
            'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 根据实际页面结构提取用户ID
        user_elem = container.select_one('h5.user-bar-uname')
        if user_elem:
            comment['user_id'] = user_elem.get_text(strip=True)
        
        # 如果主要选择器没找到，使用备用选择器
        if not comment['user_id']:
            user_id_selectors = [
                'h5[class*="user"]',
                'span[class*="user"]',
                'div[class*="user"]',
                'a[class*="user"]',
                'strong',
                'b'
            ]
            
            for selector in user_id_selectors:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 2:
                        comment['user_id'] = text
                        break
        
        # 提取评论时间
        time_elem = container.select_one('span.time')
        if time_elem:
            comment['comment_time'] = time_elem.get_text(strip=True)
        
        # 如果主要选择器没找到，使用备用选择器
        if not comment['comment_time']:
            time_selectors = [
                'span[class*="time"]',
                'div[class*="time"]',
                'span[class*="date"]',
                'div[class*="date"]',
                'time',
                '[datetime]'
            ]
            
            for selector in time_selectors:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True) or elem.get('datetime')
                    if text:
                        comment['comment_time'] = text
                        break
        
        # 提取评论内容
        content_elem = container.select_one('span.type-text')
        if content_elem:
            comment['comment_content'] = content_elem.get_text(strip=True)
        
        # 如果主要选择器没找到，使用备用选择器
        if not comment['comment_content']:
            content_selectors = [
                'span[class*="text"]',
                'div[class*="content"]',
                'div[class*="text"]',
                'p',
                'span[class*="comment"]',
                'div[class*="comment"]'
            ]
            
            for selector in content_selectors:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 5:
                        comment['comment_content'] = text
                        break
        
        # 提取用户位置
        location_elem = container.select_one('div.area')
        if location_elem:
            comment['user_location'] = location_elem.get_text(strip=True)
        
        # 如果主要选择器没找到，使用备用选择器
        if not comment['user_location']:
            location_selectors = [
                'div[class*="area"]',
                'span[class*="location"]',
                'div[class*="location"]',
                'span[class*="region"]',
                'div[class*="region"]'
            ]
            
            for selector in location_selectors:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if text:
                        comment['user_location'] = text
                        break
        
        # 提取点赞数
        like_elem = container.select_one('span.like-text')
        if like_elem:
            like_text = like_elem.get_text(strip=True)
            if like_text.isdigit():
                comment['like_count'] = int(like_text)
        
        # 如果主要选择器没找到，使用备用选择器
        if not comment['like_count']:
            like_selectors = [
                'span[class*="like"]',
                'div[class*="like"]',
                'span[class*="thumb"]',
                'div[class*="thumb"]',
                '[class*="count"]'
            ]
            
            for selector in like_selectors:
                elem = container.select_one(selector)
                if elem:
                    try:
                        like_text = elem.get_text(strip=True)
                        like_count = re.findall(r'\d+', like_text)
                        if like_count:
                            comment['like_count'] = int(like_count[0])
                            break
                    except:
                        pass
        
        # 如果评论内容为空，尝试从整个容器中提取文本
        if not comment['comment_content']:
            full_text = container.get_text(strip=True)
            if full_text and len(full_text) > 10:
                comment['comment_content'] = full_text
        
        # 只有当有评论内容时才返回（确保是有效评论）
        if comment['comment_content']:
            return comment
        else:
            return None
    
    def _save_single_comment(self, comment):
        """实时保存单条评论到JSON和表格文件"""
        try:
            # 添加到内存中的评论列表
            self.comments_data.append(comment)
            
            # 保存到JSON文件
            self._save_to_json()
            
            # 更新表格文件
            self._update_table()
            
            logger.info(f"✅ 评论已保存: {comment['user_id']} - {comment['comment_content'][:30]}...")
            
        except Exception as e:
            logger.error(f"保存评论失败: {e}")
    
    def _save_to_json(self):
        """保存评论数据到JSON文件"""
        try:
            data = {
                'core_event_name': self.core_event_name,
                'comments': self.comments_data,
                'total_comments': len(self.comments_data),
                'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.level2_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def _update_table(self):
        """更新Excel表格文件"""
        try:
            if not self.comments_data:
                return
            
            # 准备表格数据
            table_data = []
            for comment in self.comments_data:
                table_data.append({
                    '子事件': comment['event_title'],
                    '子事件时间': comment.get('event_time', ''),  # 需要从子事件数据中获取
                    '评论序号': comment['comment_index'],
                    '用户ID': comment['user_id'],
                    '评论时间': comment['comment_time'],
                    '评论内容': comment['comment_content'],
                    '用户位置': comment['user_location'],
                    '评论点赞量': comment['like_count']
                })
            
            # 创建DataFrame
            df = pd.DataFrame(table_data)
            
            # 保存到Excel文件
            df.to_excel(self.table_file, index=False, engine='openpyxl')

            # 可选：保存到CSV文件
            if self.csv_output_file:
                # 确保CSV目录存在
                os.makedirs(os.path.dirname(self.csv_output_file), exist_ok=True)
                df.to_csv(self.csv_output_file, index=False, encoding='utf-8-sig')
            
        except Exception as e:
            logger.error(f"更新表格文件失败: {e}")
    
    def scrape_all_comments(self, sub_events_data):
        """爬取所有子事件的评论"""
        logger.info(f"开始爬取 {len(sub_events_data)} 个子事件的评论...")
        
        total_comments = 0
        
        for i, event in enumerate(sub_events_data):
            try:
                logger.info(f"进度: {i+1}/{len(sub_events_data)} - {event['title'][:50]}...")
                
                if not event.get('link'):
                    logger.warning(f"事件 {event['title']} 没有链接，跳过")
                    continue
                
                # 为评论添加子事件时间信息
                event_time = event.get('time', '')
                
                comments = self.scrape_comments_from_url(
                    event['link'], 
                    event['title'], 
                    event['id']
                )
                
                # 为每条评论添加子事件时间
                for comment in comments:
                    comment['event_time'] = event_time
                
                # 若无评论，添加占位行以在表格中占据一行
                if len(comments) == 0:
                    placeholder_comment = {
                        'event_title': event['title'],
                        'event_id': event['id'],
                        'event_url': event.get('link', ''),
                        'comment_index': 0,
                        'user_id': '',
                        'comment_time': '',
                        'comment_content': '',
                        'user_location': '',
                        'like_count': 0,
                        'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'event_time': event_time
                    }
                    # 直接保存占位评论，确保顺序与一级数据一致
                    self._save_single_comment(placeholder_comment)
                
                total_comments += len(comments)
                
                # 显示进度
                print(f"✅ {i+1}/{len(sub_events_data)} - {event['title'][:30]}... - {len(comments)} 条评论")
                
                # 避免请求过快
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"处理事件 {event['title']} 失败: {e}")
                continue
        
        logger.info(f"评论爬取完成，共获取 {total_comments} 条评论")
        return total_comments
    
    def print_summary(self):
        """打印摘要信息"""
        print("\n" + "="*60)
        print("二级界面评论爬取结果摘要")
        print("="*60)
        print(f"核心事件: {self.core_event_name}")
        print(f"总评论数: {len(self.comments_data)}")
        print(f"JSON文件: {self.level2_file}")
        print(f"表格文件: {self.table_file}")
        
        if self.comments_data:
            # 统计信息
            events_with_comments = len(set(comment['event_title'] for comment in self.comments_data))
            print(f"有评论的事件数: {events_with_comments}")
            
            # 显示前几条评论
            print(f"\n前5条评论:")
            for i, comment in enumerate(self.comments_data[:5]):
                print(f"{i+1}. {comment['user_id']} ({comment['user_location']}) - {comment['comment_time']}")
                print(f"   内容: {comment['comment_content'][:50]}...")
                print(f"   点赞: {comment['like_count']}")
                print()
        
        print("="*60)
    
    def close(self):
        """关闭资源"""
        if self.driver:
            self.driver.quit()
        self.session.close()

def main():
    """主函数 - 测试单个页面"""
    # 测试URL
    test_url = "https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt_5286341969287675595&sourceFrom=search_a"
    
    scraper = Level2Scraper("抗日战争暨反法西斯战争胜利80周年")
    try:
        comments = scraper.scrape_comments_from_url(test_url, "测试事件", "test_001")
        print(f"\n✅ 测试完成，获取到 {len(comments)} 条评论")
        scraper.print_summary()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
