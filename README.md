# 键盘按键显示工具(KPS)

## 项目概述
这是一个基于 PyQt6 的键盘按键显示工具(KPS)，包含两个主要窗口：
1. **显示窗口**：实时展示用户按下的按键
2. **控制窗口**：提供配置界面控制显示效果

## 主要功能
- 高DPI支持
- 暗色主题支持
- 按键监听和显示
- 网格显示功能
- 多语言支持
- 异常捕获和日志记录
pyinstaller --onefile --windowed --name Mercy_kps main.py
## 安装步骤
```bash
# 克隆仓库
git clone https://github.com/your-repo/kps.git

# 安装依赖
pip install -r requirements.txt
```

## 使用说明
```bash
# 启动应用
python main.py
```
启动后会出现两个窗口：
1. **显示窗口**：透明背景，显示当前按下的按键
2. **控制窗口**：配置显示参数

### 详细操作指南

#### 添加按键
1. 在**控制窗口**中：
   - 点击工具栏上的"+"按钮
   - 或通过菜单：操作 > 添加按键
2. 输入按键标识（如"A"、"Ctrl"等）
3. 设置初始位置和大小

#### 多选操作
1. 在**按键编辑区域**：
   - 按住 `Ctrl` 键点击多个按键
   - 或按住鼠标左键拖拽选择矩形区域
2. 选中后右键菜单选择"批量编辑"统一设置属性

#### 格式刷使用
1. 选中一个按键后：
   - 点击工具栏上的"刷子"图标
   - 或使用快捷键 `Ctrl+B`
2. 点击其他按键应用相同样式

#### 配置切换
1. **创建新配置**：
   - 菜单：文件 > 新建配置
   - 或快捷键 `Ctrl+N`
2. **切换配置**：
   - 菜单：文件 > 切换配置
   - 或使用顶部配置下拉菜单
3. **导入配置**：
   - 菜单：文件 > 导入配置
4. **导出配置**：
   - 菜单：文件 > 导出配置

#### 保存配置
- **自动保存**：每次修改后自动保存
- **手动保存**：
  - 菜单：文件 > 保存配置
  - 或快捷键 `Ctrl+S`

## 配置文件说明
配置文件位于 `setting.json`，包含以下配置项：
```json
{
  "version": "1.0",
  "language": "zh_CN",
  "display_window": {
    "x": 1367,
    "y": 757,
    "width": 600,
    "height": 400,
    "monitor": 0,
    "background_color": [0, 0, 0, 0],
    "grid_visible": true,
    "grid_size": 3,
    "grid_color": [255, 255, 255]
  }
}
```

## 项目结构
```
├── main.py                # 应用入口
├── core/                  # 核心模块
│   ├── config_manager.py  # 配置管理
│   ├── events.py          # 事件处理
│   ├── i18n.py            # 国际化支持
│   └── key_listener.py    # 按键监听
├── widgets/               # 自定义控件
│   ├── color_button.py    # 颜色选择按钮
│   ├── grid_canvas.py     # 网格画布
│   ├── key_widget.py      # 按键显示组件
│   └── ...                # 其他控件
├── windows/               # 窗口模块
│   ├── control_window.py  # 控制窗口
│   └── display_window.py  # 显示窗口
└── assets/                # 资源文件
    └── styles/
        └── dark_theme.qss # 暗色主题样式
```

## 依赖说明
```txt
PyQt6>=6.4.0      # GUI框架
pynput>=1.7.6      # 键盘监听
pywin32>=306       # Windows系统API
```

## 常见问题
1. **无法启动**：检查依赖是否安装完整
2. **按键无响应**：确保应用有管理员权限
3. **界面显示异常**：检查`assets/styles/dark_theme.qss`是否存在

## 开发指南
1. 修改配置：编辑`core/config_manager.py`
2. 添加新语言：在`core/i18n.py`中添加翻译
3. 自定义主题：编辑`assets/styles/dark_theme.qss`