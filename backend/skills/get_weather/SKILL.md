---
name: get_weather
description: 获取指定城市的实时天气信息
---

# 获取天气技能

## 功能说明
此技能用于获取指定城市的实时天气信息。

## 使用步骤
1. 使用 `fetch_url` 工具访问天气API
2. 解析返回的JSON数据
3. 提取天气信息并格式化返回

## 示例代码
```python
import json

# 使用fetch_url获取天气数据
url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid=YOUR_API_KEY&units=metric&lang=zh_cn"
data = fetch_url(url)

# 解析JSON数据
weather_data = json.loads(data)

# 提取天气信息
city_name = weather_data.get("name")
temperature = weather_data.get("main", {}).get("temp")
humidity = weather_data.get("main", {}).get("humidity")
weather_description = weather_data.get("weather", [{}])[0].get("description")

# 格式化返回
result = f"{city_name}的当前天气：{weather_description}，温度：{temperature}°C，湿度：{humidity}%"
```

## 注意事项
- 需要替换API_KEY为实际的OpenWeatherMap API密钥
- 城市名称可以是中文或英文