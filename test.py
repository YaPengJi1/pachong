#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量检测百度事件页面的有效record_id（优化版）
- 并行检测
- 时间过滤（只保留2025年1月1日之后的事件）
- 实时保存结果
"""

import requests
import concurrent.futures
import time
import json
import re
import threading
import csv
from datetime import datetime, date
from bs4 import BeautifulSoup
import os

class RecordIdChecker:
    def __init__(self, output_file='valid_record_ids.csv'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.baidu.com/',
        })
        
        self.output_file = output_file
        self.valid_ids = []
        self.new_records = []  # 新发现的记录
        self.lock = threading.Lock()
        self.min_date = date(2025, 1, 1)  # 最小日期：2025年1月1日
        
        # 加载已保存的结果
        self.load_existing_results()
    
    def load_existing_results(self):
        """加载已保存的结果"""
        try:
            if os.path.exists(self.output_file):
                # 尝试读取文件，处理NUL字符问题
                with open(self.output_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # 移除NUL字符
                    content = content.replace('\x00', '')
                
                # 重新写入清理后的内容
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 重新读取
                with open(self.output_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    self.valid_ids = list(reader)
                print(f"📁 已加载 {len(self.valid_ids)} 个已保存的有效ID")
            else:
                self.valid_ids = []
                print("📁 未找到已保存的结果文件，从头开始")
        except Exception as e:
            print(f"❌ 加载已有结果失败: {e}")
            print("🔄 创建新的结果文件...")
            self.valid_ids = []
    
    def translate_to_english(self, chinese_text):
        """翻译中文到英文"""
        try:
            # 简单的翻译映射（可以扩展）
            translations = {
                'iPhone17脉络卡': 'iPhone17_Timeline',
                '2023年10月巴以冲突': 'October_2023_Israel_Palestine_Conflict',
                '抗日战争暨反法西斯战争胜利80周年': '80th_Anniversary_of_Victory_in_Anti_Japanese_War_and_World_Anti_Fascist_War',
                '美国所谓对等关税政策': 'US_Reciprocal_Tariff_Policy',
                '那英老公否认出轨': 'Na_Ying_Husband_Denies_Cheating',
                '新西兰央行降息周期开启': 'New_Zealand_Central_Bank_Interest_Rate_Cut_Cycle_Begins',
                '因腿伤被搀扶上车': 'Helped_into_Car_Due_to_Leg_Injury',
                '特朗普与普京谈判美俄乌三方会晤': 'Trump_Putin_Negotiations_US_Russia_Ukraine_Tripartite_Meeting'
            }
            
            # 如果找到直接映射，返回
            if chinese_text in translations:
                return translations[chinese_text]
            
            # 尝试部分匹配
            for key, value in translations.items():
                if key in chinese_text:
                    return value
            
            # 否则返回原标题（可以后续接入翻译API）
            return chinese_text
            
        except Exception as e:
            return chinese_text
    
    def save_results(self):
        """保存结果到CSV文件"""
        try:
            print(f"💾 开始保存 {len(self.valid_ids)} 条记录到 {self.output_file}")
            
            # 清理数据中的NUL字符
            cleaned_data = []
            for item in self.valid_ids:
                cleaned_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        cleaned_item[key] = value.replace('\x00', '')
                    else:
                        cleaned_item[key] = value
                cleaned_data.append(cleaned_item)
            
            # 简化保存逻辑，不使用锁
            with open(self.output_file, 'w', encoding='utf-8', newline='') as f:
                print(f"📝 文件创建/打开成功")
                fieldnames = ['url', 'title_chinese', 'title_english', 'update_date', 'found_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入表头
                writer.writeheader()
                print(f"📋 表头写入完成")
                
                # 写入数据
                for i, item in enumerate(cleaned_data):
                    writer.writerow(item)
                    print(f"📊 写入第 {i+1} 条记录: {item['title_chinese']}")
                
                print(f"✅ 全部 {len(cleaned_data)} 条记录保存完成！")
                
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            import traceback
            traceback.print_exc()
    
    def extract_update_time(self, content):
        """提取更新时间"""
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找更新时间元素
            time_elem = soup.find('p', class_='create-time')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                print(f"🔍 找到时间元素: {time_text}")  # 调试信息
                
                # 格式1: "更新至2025年9月10日 10:08"
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', time_text)
                if date_match:
                    year, month, day = map(int, date_match.groups())
                    return date(year, month, day)
                
                # 格式2: "更新至20250820"
                date_match = re.search(r'更新至(\d{8})', time_text)
                if date_match:
                    date_str = date_match.group(1)
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    return date(year, month, day)
            
            # 备用方法：直接在内容中搜索
            # 格式1: "更新至2025年9月10日"
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', content)
            if date_match:
                year, month, day = map(int, date_match.groups())
                return date(year, month, day)
            
            # 格式2: "更新至20250820"
            date_match = re.search(r'更新至(\d{8})', content)
            if date_match:
                date_str = date_match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return date(year, month, day)
                
        except Exception as e:
            print(f"❌ 时间解析错误: {e}")
        
        return None
    
    def check_single_id(self, record_id):
        """检查单个ID"""
        url = f"https://events.baidu.com/search/vein?platform=pc&record_id={record_id}"
        
        try:
            print(f"🔍 正在检查 ID: {record_id}")
            response = self.session.get(url, timeout=10)
            print(f"📡 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                print(f"📄 页面内容长度: {len(content)} 字符")
                
                # 检查是否包含事件页面特征
                if any(keyword in content for keyword in ['更新至', '全部', '时间倒序']):
                    print(f"✅ ID {record_id} 包含事件页面特征")
                    
                    # 提取更新时间
                    print(f"🕐 开始提取时间...")
                    update_date = self.extract_update_time(content)
                    print(f"📅 解析到时间: {update_date}")
                    
                    # 时间过滤：只保留2025年1月1日之后的事件
                    if update_date and update_date >= self.min_date:
                        print(f"✅ 时间符合要求，开始提取标题...")
                        title = self.extract_title(content)
                        print(f"📝 提取到标题: {title}")
                        
                        print(f"🌐 开始翻译...")
                        title_english = self.translate_to_english(title)
                        print(f"🌐 翻译结果: {title_english}")
                        
                        result = {
                            'url': url,
                            'title_chinese': title,
                            'title_english': title_english,
                            'update_date': update_date.isoformat(),
                            'found_time': datetime.now().isoformat()
                        }
                        
                        print(f"💾 添加到新记录列表...")
                        # 添加到新记录列表，不立即保存
                        self.new_records.append(result)
                        
                        print(f"✅ ID {record_id} 添加到新记录列表!")
                        return result
                    else:
                        reason = f'时间过旧: {update_date}' if update_date else '无法解析时间'
                        print(f"⏰ ID {record_id} 时间过滤: {reason}")
                    return {
                        'id': record_id,
                            'status': 'filtered',
                            'reason': reason
                    }
                else:
                    print(f"❌ ID {record_id} 不包含事件页面特征")
                        
        except Exception as e:
            print(f"❌ ID {record_id} 请求失败: {e}")
        
        return {'id': record_id, 'status': 'invalid'}
    
    def extract_title(self, content):
        """提取页面标题"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            title_elem = soup.find('title')
            if title_elem:
                return title_elem.get_text(strip=True)
            
            # 备用方法
            title_match = re.search(r'<title>(.*?)</title>', content)
            return title_match.group(1) if title_match else 'Unknown'
        except:
            return 'Unknown'
    
    def batch_check(self, start_id=591500, end_id=800000, max_workers=15, use_parallel=False, batch_size=100):
        """批量检测"""
        print(f"🔍 开始检测 record_id {start_id} 到 {end_id}")
        print(f"📅 只保留 {self.min_date} 之后的事件")
        print(f"💾 结果实时保存到 {self.output_file}")
        print(f"🔄 处理模式: {'并行' if use_parallel else '串行'}")
        if use_parallel:
            print(f"📦 批次大小: {batch_size} (每{batch_size}个ID暂停整理一次)")
        
        total_checked = 0
        valid_count = 0
        filtered_count = 0
        
        if use_parallel and max_workers > 1:
            # 并行处理模式 - 分批处理
            print(f"🚀 使用 {max_workers} 个线程并行处理")
            
            for batch_start in range(start_id, end_id + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, end_id)
                print(f"\n📦 处理批次: {batch_start} - {batch_end}")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交当前批次的任务
                    future_to_id = {
                        executor.submit(self.check_single_id, i): i 
                        for i in range(batch_start, batch_end + 1)
                    }
                    
                    # 处理当前批次的结果
                    batch_results = []
                    for future in concurrent.futures.as_completed(future_to_id):
                        result = future.result()
                        batch_results.append(result)
                        total_checked += 1
                        
                        if result.get('status') == 'valid':
                            valid_count += 1
                            print(f"✅ [{total_checked}/{end_id-start_id+1}] 发现有效ID: {result['id']}")
                        elif result.get('status') == 'filtered':
                            filtered_count += 1
                            print(f"⏰ [{total_checked}/{end_id-start_id+1}] 时间过滤: {result['id']} - {result['reason']}")
                        elif result.get('status') == 'invalid':
                            print(f"❌ [{total_checked}/{end_id-start_id+1}] 无效ID: {result['id']}")
                        else:
                            # 直接保存的结果
                            valid_count += 1
                            print(f"✅ [{total_checked}/{end_id-start_id+1}] 发现有效ID: {result.get('id', 'unknown')}")
                    
                    # 批次完成，整理排序
                    print(f"🔄 批次完成，开始整理排序...")
                    self.sort_and_save_results()
                    print(f"✅ 排序完成，继续下一批次")
                    
                    # 进度显示
                    print(f"📊 已检测 {total_checked}/{end_id-start_id+1} 个ID，有效: {valid_count}，过滤: {filtered_count}")
        else:
            # 串行处理模式（默认）
            print(f"🔄 使用串行处理模式")
            for record_id in range(start_id, end_id + 1):
                print(f"\n🔄 处理 ID {record_id} ({total_checked + 1}/{end_id-start_id+1})")
                result = self.check_single_id(record_id)
                total_checked += 1
                
                if 'status' in result:
                    if result['status'] == 'valid':
                        valid_count += 1
                        print(f"✅ 发现有效ID: {record_id}")
                    elif result['status'] == 'filtered':
                        filtered_count += 1
                        print(f"⏰ 时间过滤: {record_id} - {result['reason']}")
                    else:
                        print(f"❌ 无效ID: {record_id}")
                else:
                    # 直接保存的结果
                    valid_count += 1
                    print(f"✅ 发现有效ID: {record_id}")
        
        print(f"\n🎉 检测完成！")
        print(f"📊 总检测: {total_checked} 个ID")
        print(f"✅ 有效ID: {valid_count} 个")
        print(f"⏰ 时间过滤: {filtered_count} 个")
        
        # 最后保存所有新发现的记录
        if hasattr(self, 'new_records') and self.new_records:
            print(f"💾 开始保存所有新发现的 {len(self.new_records)} 条记录...")
            self.sort_and_save_results()
        
        print(f"💾 结果已保存到 {self.output_file}")
        
        return self.valid_ids
    
    def sort_and_save_results(self):
        """只对新发现的记录进行排序和追加保存"""
        try:
            print(f"🔄 开始处理新发现的记录...")
            
            # 只处理新发现的记录，不重新排序所有记录
            if hasattr(self, 'new_records') and self.new_records:
                print(f"📝 发现 {len(self.new_records)} 条新记录，追加保存")
                
                # 按record_id排序新记录
                def extract_record_id(url):
                    try:
                        match = re.search(r'record_id=(\d+)', url)
                        return int(match.group(1)) if match else 0
                    except:
                        return 0
                
                self.new_records.sort(key=lambda x: extract_record_id(x['url']))
                print(f"✅ 新记录排序完成")
                
                # 追加保存新记录
                self.append_new_records()
            else:
                print(f"ℹ️ 没有新记录需要保存")
            
        except Exception as e:
            print(f"❌ 处理新记录失败: {e}")
            import traceback
            traceback.print_exc()
    
    def append_new_records(self):
        """追加新记录到CSV文件"""
        try:
            if not hasattr(self, 'new_records') or not self.new_records:
                return
                
            print(f"💾 开始追加 {len(self.new_records)} 条新记录到 {self.output_file}")
            
            # 清理数据中的NUL字符
            cleaned_data = []
            for item in self.new_records:
                cleaned_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        cleaned_item[key] = value.replace('\x00', '')
                    else:
                        cleaned_item[key] = value
                cleaned_data.append(cleaned_item)
            
            # 追加模式写入
            with open(self.output_file, 'a', encoding='utf-8', newline='') as f:
                fieldnames = ['url', 'title_chinese', 'title_english', 'update_date', 'found_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入新数据
                for i, item in enumerate(cleaned_data):
                    writer.writerow(item)
                    print(f"📊 追加第 {i+1} 条记录: {item['title_chinese']}")
                
                print(f"✅ 全部 {len(cleaned_data)} 条新记录追加完成！")
            
            # 清空新记录列表
            self.new_records = []
                
        except Exception as e:
            print(f"❌ 追加保存失败: {e}")
            import traceback
            traceback.print_exc()

def main():
    # 创建检测器实例
    checker = RecordIdChecker('valid_record_ids.csv')
    
    # 检测范围（建议先小范围测试）
    print("🚀 开始批量检测...")
    print("💡 建议先用小范围测试，如 start_id=1, end_id=1000")
    
    # 可以调整检测范围和并行设置
    # 串行模式（推荐，稳定）
    #valid_ids = checker.batch_check(start_id=701198, end_id=701198, max_workers=1, use_parallel=False)
    
    # 并行模式（可选，速度快但可能不稳定）
    valid_ids = checker.batch_check(start_id=592000, end_id=800000, max_workers=15, use_parallel=True, batch_size=1000)
    
    # 显示统计信息
    print(f"\n📊 最终统计:")
    print(f"✅ 找到 {len(valid_ids)} 个2025年1月1日之后的有效ID")
    
    # 显示结果
    if valid_ids:
        print(f"\n📋 找到的有效ID:")
        for item in valid_ids:
            print(f"  URL: {item['url']}")
            print(f"  中文标题: {item['title_chinese']}")
            print(f"  英文标题: {item['title_english']}")
            print(f"  更新时间: {item['update_date']}")
            print(f"  发现时间: {item['found_time']}")
            print("  " + "-"*50)
    
    print(f"\n💾 结果已保存到 valid_record_ids.csv")

if __name__ == "__main__":
    main()