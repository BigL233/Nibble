# Nibble

Nibble 是一个面向网络小说的本地桌面工具，集成小说抓取、TXT 转 EPUB、大模型翻译、术语表管理和翻译进度控制。项目目前以 Windows 桌面使用为主，界面默认中文，也可以在设置中切换为英文。

> 本项目仅用于个人学习、备份和阅读场景。请遵守目标网站的服务条款和当地法律法规，不要用于侵犯版权或绕过付费内容。

## 截图

后续可在这里补充图片：

```md
![主界面](images/main.png)
![翻译界面](images/translate.png)
![术语表](images/glossary.png)
```

## 主要功能

- 桌面窗口界面，不再依赖终端菜单操作。
- 支持中文 / 英文界面，默认中文。
- 支持抓取已适配站点的小说目录和章节内容。
- 支持将 TXT 章节文件夹转换为 EPUB。
- 支持抓取完成后直接生成 EPUB。
- 支持通过 OpenAI 兼容接口调用大模型翻译。
- 支持 TXT 文件夹和 EPUB 两种翻译来源。
- 支持配置 API 地址、API Key，并测试接口获取模型列表。
- 支持文风指导，用于控制 AI 翻译风格。
- 支持自定义 AI 术语生成规范，用于控制机器术语表提取范围。
- 支持人工术语表导入、导出、搜索、编辑。
- 支持 AI 自动增加机器术语表，并自动保存。
- 翻译时可查看当前术语表，双击术语即可编辑。
- 支持翻译进度条、总耗时、平均每章耗时、暂停、继续和结束翻译。
- 支持使用 `Nibble_background.jpg` 作为程序背景图。

## 环境要求

- Windows 10 / Windows 11
- Python 3.10 或更高版本
- Google Chrome 115 或更高版本，建议使用最新版
- 程序会优先使用 Selenium Manager 自动匹配 ChromeDriver；如自动匹配失败，可使用程序内的重置 / 自动下载逻辑，或手动配置与本机 Chrome 主版本一致的 ChromeDriver

ChromeDriver 不需要固定为某一个版本。它只需要和用户电脑上的 Chrome 主版本匹配，例如 Chrome 138 通常应搭配 ChromeDriver 138。项目内如附带 `chromedriver.exe`，它只是离线兜底，不代表程序只能兼容该版本。

建议使用普通 Python 环境运行。若之后需要打包为 exe，可以使用项目内的 `build_windows.ps1` 生成 Windows 便携版。

## 安装

进入项目目录后安装依赖：

```bash
pip install -r requirements.txt
```

如果你的系统里同时有多个 Python 版本，可以使用：

```bash
python -m pip install -r requirements.txt
```

## 启动

默认启动桌面界面：

```bash
python Nibble.py
```

如果需要进入旧版终端模式：

```bash
python Nibble.py --cli
```

主程序入口为 `Nibble.py`。

## 基本使用

### 抓取小说

1. 在主界面的“小说网址”输入框中输入小说目录页 URL。
2. 点击“抓取小说”。
3. 程序会启动浏览器并尝试读取目录、抓取章节。
4. 抓取结果会保存为 TXT 文件，并按配置生成 EPUB。

目前项目中重点适配过 `sbxh4.com` 这一类页面，例如：

```text
https://sbxh4.com/novel/26305
```

其他站点是否可用，取决于项目里已有的站点处理器。

### TXT 文件夹转 EPUB

1. 点击“TXT 文件夹转 EPUB”。
2. 选择包含章节 TXT 的文件夹。
3. 程序会根据章节文件名排序并生成 EPUB。

### 大模型翻译

1. 点击“大模型翻译”。
2. 填写 API 地址、API Key。
3. 点击“测试 API / 获取模型”，成功后选择模型。
4. 选择来源类型：TXT 文件夹或 EPUB。
5. 选择来源路径和输出路径。
6. 如有需要，导入人工术语表或开启“AI 自动增加术语表”。
7. 点击“开始翻译”。

翻译过程中可以：

- 查看日志。
- 查看进度条。
- 查看当前章节、总耗时、平均每章耗时。
- 暂停 / 继续翻译。
- 请求结束翻译。
- 在主窗口下方查看当前术语表。
- 双击术语直接编辑。

结束翻译并不会强行中断已经发出的 API 请求，而是在当前 API 调用结束后停止，这是为了避免输出文件损坏。

## API 地址说明

Nibble 使用 OpenAI 兼容的 Chat Completions 接口。常见填写方式示例：

```text
https://api.openai.com/v1
https://api.openai.com/v1/chat/completions
https://api.deepseek.com/v1
```

如果接口测试失败，通常需要检查：

- API 地址是否包含正确的 `/v1`。
- API Key 是否有效。
- 当前服务商是否支持 `/models` 模型列表接口。
- 网络是否能访问该 API 服务。
- 账户是否有可用额度。

## 术语表

Nibble 支持两类术语表：

- 人工术语表：由用户导入、手动新增和编辑。
- 机器术语表：由 AI 在翻译章节后自动提取并保存。

术语表会影响后续章节翻译，使角色名、专有名词、游戏术语、行业术语等保持一致。

支持的术语项字段：

```json
{
  "src": "原文术语",
  "dst": "目标译文",
  "info": "说明或分类",
  "lock": 0,
  "is_active": 1
}
```

机器术语表保存位置：

- TXT 文件夹翻译：输出目录下的 `_machine_glossary.json`
- EPUB 翻译：输出 EPUB 同名的 `*_machine_glossary.json`

## 文风指导

点击“大模型翻译”窗口中的“文风指导”，可以填写你希望 AI 遵守的翻译风格，例如：

```text
请翻译为自然流畅的简体中文，保留轻小说口吻。
角色对白要口语化，叙述部分保持清晰，不要过度文言化。
专有名词必须优先遵守术语表。
```

保存后，后续翻译会自动带上这段指导。

## 术语生成规范

点击“大模型翻译”窗口中的“术语生成规范”，可以修改 AI 自动提取机器术语表时遵守的规则。比如可以要求 AI 更关注角色名、游戏技能、组织名，也可以限制它不要收录普通词语。

保存后，开启“AI 自动增加术语表”时会自动使用这份规范。

## 背景图

主界面会自动读取项目根目录下的 `Nibble_background.jpg` 作为背景图。图片会按窗口大小自适应铺满，并叠加一层暖色透明遮罩，使按钮和文字更容易阅读。

## 配置文件

项目会使用 `config.json` 保存本地设置，例如：

- ChromeDriver 路径
- 下载格式
- 界面语言
- API 地址
- 模型名
- 文风指导
- 术语生成规范
- 上次打开的翻译来源和输出路径

如果配置混乱，可以在程序中点击“重置 ChromeDriver”，或手动检查 `config.json`。

## 打包说明

推荐先打包为 Windows 便携版。便携版不需要用户安装 Python，用户解压后双击 `Nibble.exe` 即可运行。

项目已经提供 `build_windows.ps1`，可以直接用于打包。脚本会自动执行以下步骤：

- 安装 `requirements.txt` 中的运行依赖。
- 安装 PyInstaller。
- 清理旧的 `build` 和 `dist` 目录。
- 调用 PyInstaller 生成 `dist\Nibble` 便携目录。
- 复制 `README.md`、`LICENSE` 和 `config.example.json` 到分发目录。
- 如果项目根目录存在 `chromedriver.exe`，会把它一起放进分发包作为离线兜底。

### 构建便携版

在项目根目录打开 PowerShell，运行：

```powershell
.\build_windows.ps1
```

如果 PowerShell 阻止脚本运行，可以在当前窗口临时放宽执行策略后再运行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_windows.ps1
```

构建完成后会生成：

```text
dist\Nibble\Nibble.exe
```

把整个 `dist\Nibble` 文件夹压缩后发给别人即可。不要只发送单独的 `Nibble.exe`，因为同目录还包含运行所需的资源文件和依赖目录。

### 分发前建议

- 不要把你自己的 `config.json` 放进分发包，里面可能包含 API Key 和本机路径。
- 可以保留 `config.example.json`，用户需要时可参考它。
- 保留 `Nibble_background.jpg`，程序会把它作为背景图使用。
- 如果包内包含 `chromedriver.exe`，它会作为离线兜底；程序仍会优先尝试自动匹配用户本机 Chrome 对应的 ChromeDriver。
- 用户电脑仍然需要安装 Google Chrome。
- 用户 Chrome 版本过旧时，建议先升级 Chrome。Chrome 115 以下版本的驱动下载和自动匹配不如新版稳定。
- 如果杀毒软件误报，可以尝试使用 `--onedir` 便携目录分发，而不是单文件 exe。

### 做安装程序

如果之后想做真正的安装包，可以先用 `build_windows.ps1` 生成 `dist\Nibble`，再用 Inno Setup 或 NSIS 把这个文件夹打成安装程序。安装程序本质上只是把便携版复制到用户电脑，并创建桌面快捷方式。

## 常见问题

### 为什么结束翻译不是立刻停止？

因为当前 API 请求已经发出，程序会等待这次请求返回后再停止。这样可以减少半章输出、空文件或 EPUB 损坏的概率。

### 为什么机器术语表不是实时逐句更新？

机器术语表是在每章翻译完成后，由 AI 根据原文和译文提取新增术语。因此它通常会按章节批量更新。

### 为什么有些网站抓不到？

不同网站结构和反爬机制不同。Nibble 只能稳定处理已经适配过的站点。遇到新站点时，通常需要新增对应的目录解析和正文提取逻辑。

## License

本项目沿用原项目许可证，详见 [LICENSE](LICENSE)。
