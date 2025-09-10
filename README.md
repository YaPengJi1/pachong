# 百度事件评论爬虫 v2.0.0

一个专门用于爬取百度事件时间线页面及其子事件页面评论数据的完整爬虫系统。

## 🎯 项目目标

爬取百度事件时间线页面（抗日战争暨反法西斯战争胜利80周年）的：
- **一级界面**：核心事件信息 + 164个子事件列表
- **二级界面**：每个子事件页面的用户评论数据

## 📊 数据需求

### 一级界面数据
- 核心事件名称：`抗日战争暨反法西斯战争胜利80周年`
- 最新更新时间：`更新至2025年9月5日 07:53`
- 子事件数量：`164`
- 子事件列表：标题、时间、链接、摘要、作者

### 二级界面数据（评论）
- 用户ID：`百度网友e041fff`
- 评论时间：`09-04 10:16`
- 评论内容：`在一点上，我与美国总统达成一致的观点。`
- 用户地区：`江苏`
- 点赞数量：`1706`

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行爬虫
```bash
python main.py
```

### 3. 选择操作模式
- `1` - 完整爬取流程（推荐）
- `2` - 只爬取一级界面
- `3` - 只爬取二级界面
- `4` - 测试单个页面
- `5` - 查看数据摘要

## 📁 项目结构

```
pachong/
├── requirements.txt          # 依赖包
├── README.md               # 项目说明
├── requirements.md         # 详细需求说明
├── main.py                # 主执行脚本
├── level1_scraper.py      # 一级界面爬虫
├── level2_scraper.py      # 二级界面爬虫
├── data_manager.py        # 数据管理和进度显示
└── data/                  # 数据存储目录
    ├── level1_data.json   # 一级界面数据
    ├── level2_data.json   # 二级界面数据
    ├── combined_data.json  # 合并数据
    └── comments_data.csv   # CSV格式评论数据
```

## 🔧 核心功能

### Level1Scraper（一级界面爬虫）
- 提取核心事件信息
- 爬取164个子事件列表
- 处理动态内容加载
- 阶段性数据保存

### Level2Scraper（二级界面爬虫）
- 批量爬取子事件页面
- 提取用户评论数据
- 进度显示和错误处理
- 支持重试机制

### DataManager（数据管理）
- 统一数据存储格式
- 进度显示和统计
- 数据合并和导出
- CSV格式导出

## 📈 使用示例

### 完整爬取流程
```python
from main import BaiduEventScraper

scraper = BaiduEventScraper()
scraper.run_full_scrape()
```

### 单独测试
```python
from level2_scraper import Level2Scraper

scraper = Level2Scraper()
comments = scraper.scrape_comments_from_url(
    "https://mbd.baidu.com/newspage/data/videolanding?nid=sv_11083689302196204111",
    "测试事件",
    "test_id"
)
```

## 📊 输出格式

### JSON格式
```json
{
  "core_info": {
    "core_event_name": "抗日战争暨反法西斯战争胜利80周年",
    "update_time": "更新至2025年9月5日 07:53",
    "sub_event_count": 164
  },
  "sub_events": [...],
  "comments": [
    {
      "user_id": "百度网友e041fff",
      "comment_time": "09-04 10:16",
      "comment_content": "在一点上，我与美国总统达成一致的观点。",
      "user_location": "江苏",
      "like_count": 1706
    }
  ]
}
```

### CSV格式
包含所有评论数据的表格格式，便于数据分析。

## ⚙️ 配置说明

### 目标URL
```python
target_url = "https://events.baidu.com/search/vein?platform=pc&record_id=648521&query=..."
```

### 爬取参数
- 页面等待时间：15秒
- 滚动等待时间：3秒
- 请求间隔：2秒
- 重试次数：3次

## 🛠️ 技术栈

- **Python 3.7+**
- **Selenium** - 动态内容处理
- **BeautifulSoup** - HTML解析
- **Requests** - HTTP请求
- **Pandas** - 数据处理
- **Chrome WebDriver** - 浏览器自动化

## 📝 注意事项

1. **网络环境**：确保网络连接稳定
2. **Chrome浏览器**：需要安装Chrome浏览器和ChromeDriver
3. **爬取频率**：内置延迟机制，避免对服务器造成压力
4. **数据存储**：所有数据自动保存到`data/`目录
5. **错误处理**：支持断点续传和错误重试

## 🔍 故障排除

### 常见问题
1. **ChromeDriver错误**：确保ChromeDriver版本与Chrome浏览器匹配
2. **网络超时**：检查网络连接，可能需要使用代理
3. **页面结构变化**：如果爬取失败，可能是页面结构发生了变化

### 调试模式
```python
# 测试单个页面
python main.py
# 选择选项4进行测试
```

## 📈 性能优化

- 使用无头浏览器模式
- 批量处理减少请求次数
- 阶段性保存防止数据丢失
- 智能重试机制

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

MIT License

---

**版本**: v2.0.0  
**更新时间**: 2025-09-10  
**作者**: AI Assistant