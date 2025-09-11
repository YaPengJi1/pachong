#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行指定核心事件的完整爬取流程，并将结果保存到自定义目录/CSV
"""

from level1_scraper import Level1Scraper
import os
import csv
import argparse


def run_full_scrape(target_url: str, output_dir: str, csv_filename: str):
    scraper = Level1Scraper()
    try:
        if scraper.scrape_core_info(target_url) and scraper.scrape_sub_events(target_url):
            # 覆盖默认的保存位置到 output_dir
            os.makedirs(output_dir, exist_ok=True)
            # 一级页面爬取后立即保存
            scraper.save_data(os.path.join(output_dir, 'level1_data.json'))
            scraper.print_summary()

            # 组装CSV输出文件路径
            csv_output = os.path.join(output_dir, csv_filename)

            # 启动二级，定向输出
            # 二级页面：每条评论实时保存（由 Level2Scraper 实现），并输出到指定目录
            scraper.start_level2_scraping(output_dir=output_dir, csv_output_file=csv_output)
        else:
            print('❌ 爬取失败：无法获取核心信息或子事件')
    finally:
        scraper.close()


if __name__ == '__main__':
    # ========== 批量模式：基于CSV的url列进行批量爬取 ==========
    # 请在这里填写CSV文件路径（包含表头，必须包含名为 url 的列）
    # 示例：csv_path = r'D:\web-agent\pachong\result_2025-05-01_to_2025-09-11.csv'
    csv_path = r'result_2025-05-01_to_2025-09-11.csv'  # <- 在此填写CSV路径

    # 从CSV的第几行开始（>=2，因为第一行为表头），到第几行结束（包含，留空则到文件末尾）
    # 例如：start_row = 2, end_row = 100 代表处理第2行到第100行
    start_row = 2
    end_row = 4  # 或者填写具体的行号，例如 200

    # 命令行参数/交互式输入，覆盖上述行号配置
    parser = argparse.ArgumentParser(description='Batch scrape Baidu events from a CSV file of URLs.')
    parser.add_argument('--start-row', type=int, help='起始行号（>=2）')
    parser.add_argument('--end-row', type=int, help='结束行号（可选，包含该行）')
    args, _unknown = parser.parse_known_args()

    if args.start_row is not None:
        start_row = args.start_row
    else:
        try:
            user_input = input(f'请输入起始行号(>=2，默认 {start_row}): ').strip()
            if user_input:
                start_row = int(user_input)
        except Exception:
            pass

    if args.end_row is not None:
        end_row = args.end_row
    else:
        try:
            user_input = input('请输入结束行号(可留空，留空代表到文件末尾): ').strip()
            if user_input:
                end_row = int(user_input)
        except Exception:
            pass

    if start_row is None or start_row < 2:
        print('⚠️ 起始行号无效，已重置为 2')
        start_row = 2

    if csv_path:
        # 批量读取并逐行爬取
        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            # 将行号与数据对齐：header在文件第1行，数据从第2行开始
            for idx, row in enumerate(reader, start=2):
                if idx < start_row:
                    continue
                if end_row is not None and idx > end_row:
                    break

                url = (row.get('url') or '').strip()
                if not url:
                    print(f'⏭️ 第 {idx} 行缺少 url，已跳过')
                    continue

                seq = idx - 1  # 序号 = 行号 - 1（第2行对应序号1）
                out_dir = os.path.join('data_BAI_DU', str(seq))
                out_csv_name = f'{seq}.csv'

                print(f'🚀 开始处理 第 {idx} 行（序号 {seq}）：{url}')
                try:
                    run_full_scrape(url, out_dir, out_csv_name)
                except Exception as e:
                    print(f'❌ 第 {idx} 行（序号 {seq}）处理失败：{e}')
        print('✅ 批量处理完成')
    else:
        # ========== 单个模式（保留原功能，按需使用） ==========
        target_url = 'https://events.baidu.com/search/vein?platform=pc&record_id=708914&query=%E9%82%A3%E8%8B%B1%E8%80%81%E5%85%AC%E5%90%A6%E8%AE%A4%E5%87%BA%E8%BD%A8%3A%E5%9B%A0%E8%85%BF%E4%BC%A4%E8%A2%AB%E6%90%80%E6%89%B6%E4%B8%8A%E8%BD%A6&srcid=50367'
        output_dir = 'data/Cheating'
        csv_filename = 'Cheating.csv'
        run_full_scrape(target_url, output_dir, csv_filename)

        #    python main.py --start-row 2 --end-row 100