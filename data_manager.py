#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度事件评论爬虫 - 数据管理和进度显示
负责数据存储、进度显示和结果合并
"""

import json
import time
import os
import pandas as pd
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, output_dir: str = 'data'):
        self.data_dir = output_dir or 'data'
        self.level1_file = os.path.join(self.data_dir, 'level1_data.json')
        self.level2_file = os.path.join(self.data_dir, 'level2_data.json')
        self.combined_file = os.path.join(self.data_dir, 'combined_data.json')
        self.csv_file = os.path.join(self.data_dir, 'comments_data.csv')
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"创建数据目录: {self.data_dir}")
    
    def save_level1_data(self, core_info, sub_events):
        """保存一级界面数据"""
        try:
            data = {
                'core_info': core_info,
                'sub_events': sub_events,
                'total_sub_events': len(sub_events),
                'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.level1_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"一级界面数据已保存到: {self.level1_file}")
            return True
        except Exception as e:
            logger.error(f"保存一级界面数据失败: {e}")
            return False
    
    def save_level2_data(self, comments_data):
        """保存二级界面评论数据"""
        try:
            data = {
                'comments': comments_data,
                'total_comments': len(comments_data),
                'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.level2_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"二级界面数据已保存到: {self.level2_file}")
            return True
        except Exception as e:
            logger.error(f"保存二级界面数据失败: {e}")
            return False
    
    def load_level1_data(self):
        """加载一级界面数据"""
        try:
            if os.path.exists(self.level1_file):
                with open(self.level1_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"加载一级界面数据失败: {e}")
            return None
    
    def load_level2_data(self):
        """加载二级界面数据"""
        try:
            if os.path.exists(self.level2_file):
                with open(self.level2_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"加载二级界面数据失败: {e}")
            return None
    
    def combine_data(self):
        """合并一级和二级数据"""
        try:
            level1_data = self.load_level1_data()
            level2_data = self.load_level2_data()
            
            if not level1_data or not level2_data:
                logger.error("无法合并数据：缺少一级或二级数据")
                return False
            
            combined_data = {
                'project_info': {
                    'name': '百度事件评论爬虫',
                    'description': '爬取百度事件时间线页面及其子事件页面的评论数据',
                    'version': '2.0.0',
                    'create_time': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'core_event': level1_data['core_info'],
                'sub_events': level1_data['sub_events'],
                'comments': level2_data['comments'],
                'statistics': {
                    'total_sub_events': level1_data['total_sub_events'],
                    'total_comments': level2_data['total_comments'],
                    'events_with_comments': len(set(comment['event_title'] for comment in level2_data['comments'])),
                    'level1_scrape_time': level1_data['scrape_time'],
                    'level2_scrape_time': level2_data['scrape_time']
                }
            }
            
            with open(self.combined_file, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"合并数据已保存到: {self.combined_file}")
            return True
        except Exception as e:
            logger.error(f"合并数据失败: {e}")
            return False
    
    def export_to_csv(self):
        """导出评论数据到CSV"""
        try:
            level2_data = self.load_level2_data()
            if not level2_data or not level2_data['comments']:
                logger.error("没有评论数据可导出")
                return False
            
            # 转换为DataFrame
            df = pd.DataFrame(level2_data['comments'])
            
            # 保存为CSV
            df.to_csv(self.csv_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"CSV数据已导出到: {self.csv_file}")
            return True
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False
    
    def print_progress(self, current, total, message=""):
        """打印进度信息"""
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * current // total) if total > 0 else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f"\r进度: |{bar}| {percentage:.1f}% ({current}/{total}) {message}", end='', flush=True)
        
        if current == total:
            print()  # 换行
    
    def print_summary(self):
        """打印完整摘要"""
        print("\n" + "="*80)
        print("📊 百度事件评论爬虫 - 完整摘要")
        print("="*80)
        
        # 加载数据
        level1_data = self.load_level1_data()
        level2_data = self.load_level2_data()
        
        if level1_data:
            core_info = level1_data['core_info']
            print(f"🎯 核心事件: {core_info.get('core_event_name', '未获取')}")
            print(f"⏰ 更新时间: {core_info.get('update_time', '未获取')}")
            print(f"📝 子事件数量: {level1_data.get('total_sub_events', 0)}")
            print(f"📅 一级爬取时间: {level1_data.get('scrape_time', '未获取')}")
        
        if level2_data:
            print(f"💬 总评论数: {level2_data.get('total_comments', 0)}")
            print(f"📅 二级爬取时间: {level2_data.get('scrape_time', '未获取')}")
            
            if level2_data.get('comments'):
                events_with_comments = len(set(comment['event_title'] for comment in level2_data['comments']))
                print(f"📰 有评论的事件数: {events_with_comments}")
        
        print("\n📁 数据文件:")
        files = [self.level1_file, self.level2_file, self.combined_file, self.csv_file]
        for file in files:
            if os.path.exists(file):
                size = os.path.getsize(file)
                print(f"  ✅ {file} ({size} bytes)")
            else:
                print(f"  ❌ {file} (不存在)")
        
        print("="*80)
    
    def get_statistics(self):
        """获取统计信息"""
        try:
            level1_data = self.load_level1_data()
            level2_data = self.load_level2_data()
            
            stats = {
                'level1_available': level1_data is not None,
                'level2_available': level2_data is not None,
                'total_sub_events': level1_data.get('total_sub_events', 0) if level1_data else 0,
                'total_comments': level2_data.get('total_comments', 0) if level2_data else 0,
                'events_with_comments': 0
            }
            
            if level2_data and level2_data.get('comments'):
                stats['events_with_comments'] = len(set(comment['event_title'] for comment in level2_data['comments']))
            
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

def main():
    """测试数据管理器"""
    dm = DataManager()
    
    # 测试加载数据
    level1_data = dm.load_level1_data()
    level2_data = dm.load_level2_data()
    
    if level1_data:
        print("✅ 一级数据加载成功")
    else:
        print("❌ 一级数据不存在")
    
    if level2_data:
        print("✅ 二级数据加载成功")
    else:
        print("❌ 二级数据不存在")
    
    # 显示摘要
    dm.print_summary()

if __name__ == "__main__":
    main()
