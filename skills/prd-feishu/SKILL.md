---
name: prd-feishu
description: "先制作并审查可操作的单文件 HTML 原型，再写 PRD；从原型截取对应页面状态放入各节原型图位置，将共用 HTML 放在迭代版本文档并让需求文档引用，同步云效需求至设计中。适用于首次生成或完整重写；局部修改用 prd-feishu-edit。"
allowed-tools: Read, Write, Bash, Glob, Grep, AskUserQuestion, Agent
---

# 飞书 PRD 生成器

You are a senior product manager. 先还原用户要求的页面和完整交互，再依据审查通过的原型写产品视角 PRD、发布飞书，并把飞书 URL 回写到对应云效需求的描述顶部。

> ⚠️ **只在「首次生成 / 完整重写」时用本 skill。** 本 skill 的 `publish.py` 会
> **清空整篇文档再从本地 HTML 重写**，会抹掉用户在飞书里手动改过的内容。
> 如果用户是要**修改一份已发布的 PRD**（改文案 / 加一行 / 调某节原型图 / 改规则），
> **改用 `/prd-feishu-edit`** —— 它以飞书实时文档为准，只改用户点名的章节，
> 且先出「原内容 vs 修改后」评审子节点、批准后才合并。**不要为了「改一下」重跑本 skill。**

## 原型先行：强制审查关口

首次生成或完整重写 PRD 时，依次完成以下阶段。此关口同时适用于需求标识模式和直传 URL 模式；用户明确要求跳过原型时，以用户当次指示为准。

1. **收集页面依据。** 读取用户给的截图、录屏、文字、现有页面或其他参考，明确要做的页面、入口、可见字段、交互和业务结果。截图只证明可见状态；未展示的交互先结合用户说明、现有系统和同一需求上下文核实。仍影响方案的缺口，集中问用户，不把猜测写成确定需求。
2. **制作一个可操作的 HTML 原型。** 在项目工作区持久保存 `outputs/prd-prototypes/<需求标识或名称>/<时间戳>/prototype.html`，使用单文件 HTML（CSS、JS 内联；确需外部素材时一并固定版本）。同一迭代已有共用原型时，以其当前版本为基线，在候选副本中加入本需求交互，保留其他需求的页面与状态。按用户提供的页面风格还原，覆盖本需求范围内的完整用户路径：入口、切换、筛选或选择、表单、校验、确认或取消、结果反馈，以及相关的空态、错误态和不可操作态。按钮和链接应有对应模拟行为；只用模拟数据，不调用生产写接口。原型须能脱离 PRD 单独打开和体验。
3. **模拟用户逐步检查。** 用浏览器真实点击主要路径，检查状态是否连贯、弹窗能关闭、校验与反馈是否可见；记录简短的操作路径，给用户本地 HTML 链接审查。用户提出修改时只迭代该原型。**用户明确表示原型通过前，不写 PRD 正文，不调用 `publish.py`，不清空飞书文档，也不更新云效状态。**
4. **原型通过后写 PRD 并配图。** 以最终 HTML 中已确认的页面、状态、动作和结果为依据补齐业务规则。在每个相关功能的“原型图”小节，从同一 HTML 操作到对应状态并截取页面或弹窗，放在该小节字段表或说明附近；一图可覆盖多个相邻字段，不必机械地每个字段一图。入口、关键分支和结果态应有足够截图让读者对照交互；不相关的截图不插入。截图必须来自已审查的 HTML，不能重新画另一套 UI。若要新增超出原型的逻辑，先更新原型并复核。
5. **发布并读回。** 将已审查 HTML 上传或替换到需求 wiki 节点的**直接父级迭代版本文档**中的唯一文件块，需求 PRD 的“可交互原型”只放版本文档链接；截图仍按 PRD 位置插入图片块。运行 `publish.py --prototype-attachment`，读回 PRD 链接、截图与父级文件块后才同步云效状态。下载的 HTML 可在本地浏览器操作；飞书文档中的文件块不运行脚本。

### 版本共用原型的边界

- 每个迭代版本文档维护一个 `共用交互原型.html` 文件块。后续需求修改时更新**同一文件块**，需求文档不再各自上传 HTML 副本；不同迭代各有自己的文件。
- 需求文档必须是 wiki 节点，且直接父节点为 docx 类型的迭代版本文档。父子关系不明或父节点不支持附件时，停止发布并核对节点，不静默改放到需求文档。
- 发布前确认候选原型包含本迭代已批准的其他交互，固定其 SHA-256。需求文档中的原型截图是该需求审查时的页面状态，**不会随共用 HTML 更新**；需要更新截图时按 `prd-feishu-edit` 另行评审对应章节。
- `--prototype-attachment` 参数继续接受已批准 HTML 路径，但目的地改为迭代版本文档。发布器验证父子关系、更新父级文件块，并在当前需求 PRD 写入版本文档链接。已上传的旧需求附件须单独迁移或移除，避免读者下载到旧版。

截图位置、文件标记和验收要点见 [交互原型工作流](references/interactive-prototype.md)。

## Input

用户输入：$ARGUMENTS

参数解析（按以下顺序判定）：
1. 如果第一个参数是 URL（含 `feishu.cn/docx/` 或 `feishu.cn/wiki/`）→ **直传 URL 模式**：跳过云效查找，直接往这个 URL 写
2. 如果第一个参数不是 URL → **需求标识模式**：在 `.aliyuncs.json` 的 `requirements` 数组里按以下顺序查找：
   - `identifier` 完全相等
   - `subject` 完全相等
   - `subject` 包含该字符串（仅当唯一命中时）
   - 多义或无命中 → AskUserQuestion 让用户从列表选
3. 如果没有参数，先根据当前对话中的唯一需求、用户给的页面截图或云效工作项定位；仍不唯一时再请用户选择。截图和交互说明可以分批提供，定位后开始原型阶段。

## 主工作流（需求标识模式 = 推荐）

```
用户：/prd-feishu 应用管理详情页

skill 步骤：
1. 校验 .aliyuncs.json 存在，含 requirements 数组
2. 模糊匹配「应用管理详情页」→ 找到 requirement → 取 feishu_url
3. 如 feishu_url 为空：提示用户先确保 aliyuncs:create-requirement 已绑定飞书节点
   （旧需求可能没绑，告知用户在飞书手动建一个节点并回填 feishu_url，或重跑 create-requirement）
4. 根据截图/说明制作持久保存的 `prototype.html`，逐步点测，交用户审查；依据反馈修改到用户明确通过
5. 从通过的原型提取页面与交互规则，按 prd skill 的内容结构生成独立的 PRD HTML
6. 将原型中的对应页面状态截图，插在 PRD 每节“原型图”位置，核对截图与文案一致
7. 调用 `python3 <本 skill 目录>/publish.py <PRD_HTML> <feishu_url> --prototype-attachment <已批准的本迭代共用原型.html>`
8. publish.py 自动：
   - 写飞书内容（清空 + 插入）
   - 按 PRD 位置上传原型截图 + 绑定
   - 在直接父级版本文档中上传或替换唯一的可操作 HTML 文件块，并读回校验
   - 在需求 PRD 中写入指向该版本文档的“可交互原型”链接，不创建需求级 HTML 附件
   - 父节点 / 祖父节点向上回链
   - 反查 .aliyuncs.json 拿到 requirement.identifier，把飞书 URL 同步到云效需求描述顶部
   - 飞书正文、截图、版本共用附件与需求链接均成功后，把对应云效需求状态更新为「设计中」，并同步写回 `.aliyuncs.json`
9. 读回飞书需求文档和版本文档，核对各截图所在章节、链接、共用附件名称及原型版本，向用户交付 PRD 链接
```

## 备用工作流（直传 URL 模式 = 飞书优先，云效可选）

如果用户直接给了飞书 URL（适用于「这份 PRD 不挂在云效」的临时场景）：
1. 同样执行“原型先行”审查关口，再从通过的原型写 PRD HTML
2. 在对应章节插入已审查原型截图，调用带 `--prototype-attachment` 的 publish.py
3. publish.py 仍会尝试反查 `.aliyuncs.json` 的 feishu_url 同步描述；找不到匹配项就跳过云效同步

## 云效状态联动

- 只有飞书 PRD、各节原型截图、需求文档中的版本链接与版本文档中的共用 HTML 均已成功写入后才更新状态；原型审查、本地 PRD 草稿等中间步骤不触发。
- 按飞书 URL 中的 wiki/docx token 匹配 `.aliyuncs.json` 的需求，忽略 host、query 与尾斜杠差异。
- 目标状态固定为「设计中」，但 identifier 必须从该需求的实际工作流按名称动态解析，不得写死项目状态 ID。
- 远端已是「设计中」时视为幂等成功，仍校准 `.aliyuncs.json` 中的 `status`。
- 直传 URL 且没有匹配需求时可以跳过；已经匹配到需求但状态更新失败时，必须明确报告“飞书已发布、云效状态未更新”并以非零状态退出，不得伪报全流程成功。

## 飞书节点的来源

新工作流下，飞书空节点是 `aliyuncs:create-requirement` 自动创建的（前提是 `aliyuncs:create-iteration` 时设了 `feishu_parent_url`）。所以：
- 跑过 `aliyuncs:create-iteration` 填了飞书父节点 URL
- 跑过 `aliyuncs:create-requirement` 创建需求
- 此时 `.aliyuncs.json` 里 requirement.feishu_url 已就绪
- 直接 `/prd-feishu <subject>` 就能写文档

如果 `feishu_url` 为空（旧需求或飞书联动失败），用户需要手动在飞书建空节点（设链接共享）+ 把 URL 填回 .aliyuncs.json，或直接用「直传 URL 模式」。

## 前置检查

### 1. 读取飞书凭证

```bash
CONFIG="$HOME/.prd-feishu/config.json"
if [ ! -f "$CONFIG" ]; then
  echo "未找到飞书凭证配置。请先运行 /prd-feishu-init 完成初始化。"
  exit 1
fi
```

读取 `app_id` / `app_secret` / `app_domain`（不再需要 `default_folder_token`）。

### 2. 检查截图工具

截图时使用能操作已审查 HTML 的浏览器工具，保存 PNG 并人工核对。只有旧式 SVG / 视觉容器仍需发布器调用本机 Chrome 渲染时，才检查 Chrome 路径：

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -x "$CHROME" ]; then
  # 备选路径
  CHROME="$(which chromium 2>/dev/null || which google-chrome 2>/dev/null)"
fi
[ -z "$CHROME" ] && echo "未找到 Chrome 浏览器，请先安装 Chrome 或 Chromium。" && exit 1
```

## PRD 内容结构（与 `prd` skill 完全一致）

**PRD 结构和写作规则等同于同级 `prd` skill 的 SKILL.md**，主要章节：

1. `# 需求名称`（H1 标题，等同于飞书文档标题）
2. `## 需求目标`
3. `## 需求简述`
   - `### 3.1 产品架构图`（用嵌套列表表达，飞书 Markdown 转换后自动变成层级列表）
   - `### 3.2 功能清单`（Markdown 表格：编号 | 名称 | 类型 | 说明）
4. `## 需求详述`
   - `### 4.x 功能名`
     - `#### 4.x.1 状态机`（仅在功能有真实用户可感知的业务状态流转时画；状态机使用 SVG，发布时转 PNG）
     - `#### 4.x.2 原型图`（含对应 HTML 页面状态的截图及筛选区 / 列表区 / 表单区字段表；每个“原型图”小节至少有一张对应截图）
     - `#### 4.x.3 逻辑补充`（仅在有复杂业务逻辑时写）

### 项目级偏好规则（严守）

本项目沿用以下写作偏好：

1. **不写「数据关系」章节** — 不列后端表名 / 字段映射 / 外键
2. **产品视角，重用户体验** — 不写技术实现细节（缓存 TTL / 幂等键 / 性能 P95 等）
3. **严格按需求范围写功能改动** — 需求里没要求的功能 / 入口 / 列 / 徽章 / 提示条一律不补
4. **状态机判断准则** — 没有真实业务状态流转就**整个省略状态机小节**（连小标题也不要保留）
5. **规则类内容写「具体规则」** — 涉及评级 / 判定 / 计算 / 分级时要把每档 / 每条规则讲清楚

## 可操作 HTML 与原型截图

已审查的 `prototype.html` 是页面和交互的依据。写 PRD 时先按功能章节列出需要看到的页面状态，再从该 HTML 实际操作到这些状态截图。优先截取包含完整上下文的页面区域；弹窗可单独截，但要保留足够的页面背景以识别入口。长页面分段截图，避免缩成看不清的一张图；相同状态不要重复插图。

将 PNG 保存在原型目录的 `screenshots/` 下，文件名说明页面和状态。每张图放在**对应的 `4.x 原型图` 小节**，靠近其字段表或交互说明；不要全部放在文档末尾，也不要只放状态机图。示例：

```html
<h4>4.2.2 原型图</h4>
<h5>连接成功后的应用选择</h5>
<figure data-prd-screenshot="outputs/prd-prototypes/需求ID/时间戳/screenshots/02-应用选择.png"
        data-prototype-state="阿里云 ALB 连接成功，已扫描并勾选两个应用"
        data-prototype-sha256="已审查 prototype.html 的 SHA-256">
  <img src="outputs/prd-prototypes/需求ID/时间戳/screenshots/02-应用选择.png"
       alt="连接成功后的应用选择" style="max-width:100%;height:auto;">
  <figcaption>图：连接成功后选择应用</figcaption>
</figure>
```

- `data-prd-screenshot` 是相对 PRD HTML 所在目录的 PNG 路径；`img src` 用同一路径，让本地 PRD 也能看到图。
- `data-prototype-state` 记录截图时的页面和状态；`data-prototype-sha256` 必须等于发布时原型文件的哈希。发布器会检查这两项和图片文件，按正文顺序绑定到飞书图片块。
- 截图前核对选中态、字段值、提示和弹窗与同节文字一致。截图应可辨认表头、输入项和按钮；裁掉大块空白，保留完整的相关表格和操作。
- 不把现网截图、重新绘制的静态图或其他版本原型冒充已审查 HTML 的截图。交互原型发生变化时重新审查并重截受影响图片。
- 状态机图只在确有业务状态流转时出现，可继续用 SVG 图，但不能代替页面原型截图。

原型 HTML 默认作为迭代版本文档中的唯一附件交付；需求 PRD 只保留指向该版本文档的链接。用户从版本文档下载后可在浏览器操作；截图供直接阅读 PRD 时快速对照。截图采集与验收细节见 [交互原型工作流](references/interactive-prototype.md)。

## 实现脚本

本 skill 目录下自带 `publish.py`，封装了正文转换、按位置插图、父级版本文档中的共用 HTML 文件块、需求链接、读回校验和向上回链。发布前可用 `--prepare-only` 检查 Markdown 与图片顺序，不调用远端接口。PRD 默认用法：

```bash
python3 "<本 skill 目录>/publish.py" \
  <PRD_HTML 路径> <飞书文档 URL> \
  --prototype-attachment <已审查的本迭代共用原型.html>
```

可加 `--prototype-parent-url <版本文档 wiki URL>` 显式核对父节点；它必须与需求 wiki 的直接父节点一致。用户明确选择 HTTPS 内嵌且已提供稳定地址时，才可沿用 `--prototype-html <HTML> --prototype-url <HTTPS_URL>`。不带原型参数的旧用法仅保留给 `gray-report`、`regression-report` 等非 PRD 调用方；本 skill 的首次 PRD 流程必须传入原型。只在脚本无法满足需求时再按下方步骤逐项调用 API。

## 向上回链（自动维护目录索引）

写完 PRD 主体后，脚本会沿 wiki `parent_node_token` 自动向上爬两级，在父节点 / 祖父节点的 docx 末尾追加 / 更新一个 bullet：

- **父节点正文**追加：`- [当前 PRD 标题](当前 PRD URL) — 需求目标全文`（按 URL 查重，命中则更新简介文本）
- **祖父节点正文**追加：`- [父节点标题](父节点 URL)`（按 URL 查重，命中则跳过）

"需求目标全文"由 HTML 提取：`<h2>` 文本含「需求目标」开始，到下一个 H2 之前的所有 `<p>`。

### 适用场景

```
[祖父] 系统名     ← 自动出现一行指向「迭代版本」的 bullet
└── [父] 迭代版本  ← 自动出现 N 行，每行一个 PRD 链接 + 简介
    ├── PRD 1
    ├── PRD 2
    └── ...
```

层级不够（PRD 没有父节点 / 父节点没有祖父）时自动跳过对应级别，不报错。

## 飞书 API 调用流程

### 准备：换取 tenant_access_token

```bash
DOMAIN="$app_domain"  # 默认 open.feishu.cn
TOKEN_RESP=$(curl -s -X POST "https://$DOMAIN/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{\"app_id\":\"$APP_ID\",\"app_secret\":\"$APP_SECRET\"}")
TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")
```

token 有效期 2 小时，本次 skill 执行期间复用同一个 token。

### 步骤 1：从用户提供的 URL 解析出 doc_id

支持两种 URL 形态：

```python
import re, requests
m = re.search(r'/(docx|wiki)/([A-Za-z0-9]+)', TARGET_URL)
url_type, url_token = m.group(1), m.group(2)

if url_type == 'wiki':
    # wiki 节点要先转 docx obj_token
    r = requests.get(f'{BASE}/wiki/v2/spaces/get_node',
                     headers=HEAD, params={'token': url_token})
    node = r.json()['data']['node']
    if node['obj_type'] != 'docx':
        sys.exit('节点不是 docx 类型')
    DOC_ID = node['obj_token']
else:
    DOC_ID = url_token
```

### 步骤 1b：清空目标文档的现有内容

用户给的文档是新建的空文档（仅有根块 + 默认标题段），需要先把根块下的 children 全清掉再写：

```python
r = requests.get(f'{BASE}/docx/v1/documents/{DOC_ID}/blocks',
                 headers=HEAD, params={'page_size': 500})
items = r.json()['data']['items']
root = next(b for b in items if b['block_type'] == 1)  # block_type=1 是 page 根块
n = sum(1 for b in items if b.get('parent_id') == root['block_id'])
if n > 0:
    requests.delete(f'{BASE}/docx/v1/documents/{DOC_ID}/blocks/{DOC_ID}/children/batch_delete',
                    headers={**HEAD, 'Content-Type': 'application/json'},
                    json={'start_index': 0, 'end_index': n})
```

⚠️ **关键顺序约束**：图片素材上传时 `parent_node` 必须填**图片块的 block_id**（不是文档 ID）。所以正确流程是 **解析 URL → 清空文档 → 转换 markdown 拿 blocks → 用 descendant 接口插入 → 从响应里拿到真实 image block_id → 然后才上传 PNG → 最后 replace_image 绑定**。不能预先上传 PNG。

### 步骤 2：Markdown 拼装 + 图片占位

生成完整 Markdown 文本：

- 主体内容（标题 / 段落 / 表格 / 列表 / 引用）直接写 Markdown
- 每个原型图位置先用占位 Markdown 图片：`![原型图1](placeholder-1)`
- 占位 URL 不用真的存在，转换时飞书会把它当 Image block 处理；后续步骤会用 replace_image 替换为真实图片

### 步骤 3：Markdown 转 blocks

```bash
CONVERT_RESP=$(curl -s -X POST "https://$DOMAIN/open-apis/docx/v1/documents/blocks/convert" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{
    \"content_type\": \"markdown\",
    \"content\": $(echo "$MARKDOWN" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
  }")
```

返回 `blocks`（含层级关系的扁平数组）、`first_level_block_ids`、`block_id_to_image_urls`。

### 步骤 4：清理 blocks

- **表格 block 去除 `merge_info` 字段**（飞书要求此字段只读，传入会报错）：

```python
for b in blocks:
    if b.get('block_type') == 31:  # Table
        b.get('table', {}).get('property', {}).pop('merge_info', None)
```

### 步骤 5：用 descendant 接口插入嵌套块

⚠️ 不要用 `/children` 接口——它不支持嵌套块（含 table_cell 的表格会报 `block not support to create`）。要用 `/descendant`：

```bash
curl -s -X POST "https://$DOMAIN/open-apis/docx/v1/documents/$DOC_ID/blocks/$DOC_ID/descendant" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{
    \"index\": 0,
    \"children_id\": $FIRST_LEVEL_IDS_JSON,
    \"descendants\": $CLEANED_BLOCKS_JSON
  }"
```

返回 `data.descendants`（或 `data.children`）数组，里面是**插入后的真实 block**。⚠️ 这些 block_id 是飞书重新分配的，**跟 convert 返回的 block_id 不同**。从这里按 `block_type==27` 提取真实的图片块 ID（保持出现顺序，与原型图 PNG 序号一一对应）。

### 步骤 6：用真实 image_block_id 上传 PNG 素材

对每个原型图 PNG 调用图片素材上传 API：

```bash
# parent_node 必须填上一步拿到的真实 image_block_id
curl -s -X POST "https://$DOMAIN/open-apis/drive/v1/medias/upload_all" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file_name=proto-1.png" \
  -F "parent_type=docx_image" \
  -F "parent_node=$IMAGE_BLOCK_ID" \
  -F "size=$(stat -f%z /tmp/prd-feishu-{ts}/proto-1.png)" \
  -F "file=@/tmp/prd-feishu-{ts}/proto-1.png"
```

⚠️ 如果 `parent_node` 填了 `$DOC_ID` 而不是真实 image_block_id，下一步 replace_image 会报 `1770001 invalid param` 或 `1061044 parent node not exist`。

返回 `file_token`。

### 步骤 7：为图片块绑定上传好的素材

对每个图片块用 `update_block` 接口：

```bash
curl -s -X PATCH "https://$DOMAIN/open-apis/docx/v1/documents/$DOC_ID/blocks/$IMAGE_BLOCK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{
    \"replace_image\": {
      \"token\": \"$FILE_TOKEN\"
    }
  }"
```

`$FILE_TOKEN` 是步骤 6 上传图片素材返回的 token；`$IMAGE_BLOCK_ID` 是步骤 5 descendant 接口返回的真实图片块 ID。**按顺序一一对应**：第 N 个原型图 PNG 上传得到的 file_token，绑定到第 N 个图片块的 block_id。

### 步骤 8：在版本文档更新共用 HTML 并读回

发布器在清空需求 PRD 之前，先解析该需求 wiki 的直接父级版本文档。版本文档第一次交付时创建 `block_type=23` 的文件块；已有 `共用交互原型.html` 时复用其**内层 File block_id**。用该 ID 作为 `parent_node`、`parent_type=docx_file` 上传已审查 HTML，再对同一文件块执行 `replace_file`。读回文件块，确认 token 与文件名；随后在需求 PRD 的“可交互原型”小节写入版本文档链接。不得在需求文档再建 HTML 文件块。此步失败时不清空需求 PRD，也不更新云效状态。

## 步骤 9：输出飞书文档链接

```
✓ 飞书 PRD 已写入：
  目标：{TARGET_URL}
```

## 完整流程伪代码

```
1. 根据用户截图和交互说明做 prototype.html，模拟点击检查；用户审查，修改至明确通过
2. 从批准的原型写 PRD HTML，在每个“原型图”小节放入对应页面状态的 PNG 与标记
3. 用 --prepare-only 检查 Markdown、截图顺序与原型哈希，再调用 publish.py 正式发布
4. publish.py 验证 config、截图文件和原型文件；换 tenant_access_token，解析 URL → DOC_ID
5. 清空目标空节点并插入 PRD Markdown blocks
6. 对每个静态原型图 PNG：
    a. POST /drive/v1/medias/upload_all 上传 (parent_node=IMAGE_BLOCK_ID_N, parent_type=docx_image) → 得 FILE_TOKEN_N
    b. PATCH /docx/v1/documents/{DOC_ID}/blocks/{IMAGE_BLOCK_ID_N} replace_image=FILE_TOKEN_N
7. 在直接父级版本文档中复用或创建唯一 HTML 文件块，上传并绑定附件，GET 核对文件 token；在需求 PRD 追加指向版本文档的“可交互原型”链接
8. 回链飞书目录，更新云效描述和「设计中」状态
9. 读回飞书需求正文、各节图片、版本链接和父级附件；核对章节与截图内容，交付 PRD 链接
```

## 错误处理

| 场景 | 处理 |
|------|------|
| token 换取失败 (code != 0) | 提示用户配置可能过期，建议重新 `/prd-feishu-init` |
| URL 解析失败 | 提示用户给 docx URL（形如 `/docx/{id}` 或 `/wiki/{token}`）|
| 列 blocks 失败 (1254030 / forbidden) | 用户没把文档共享给应用，提醒：文档分享 → 链接共享 →「组织内获得链接的人可编辑」|
| 图片上传失败 (1061045 / 1061046) | 检查 PNG 文件 + parent_type 是否为 `docx_image` |
| Markdown 转换失败 | 检查 Markdown 是否含非法字符；常见是表格列数不一致 |
| 创建嵌套块失败 (1770006 schema mismatch) | 通常是 BLOCKS 没正确清理（表格 merge_info 没去掉）|
| 插入嵌套块失败 (1770029 block not support to create) | 用了 `/children` 接口，必须用 `/descendant` |
| 图片上传失败 (1061044 parent node not exist) | 用了 convert 返回的 block_id；要用 descendant 接口插入后响应里的真实 image block_id |
| 更新图片块失败 (1770001 invalid param) | parent_node 没填对（必须是真实 image_block_id，不是 DOC_ID）|
| 原型截图路径或哈希不匹配 | 回到已审查 HTML，重截对应状态并更新 PRD 中的文件路径与哈希；发布前停止 |
| “原型图”小节没有截图 | 从同一 HTML 补截对应状态；只有规则说明的小节应改名 |
| 版本共用 HTML 上传或绑定失败 | 核对父级 docx 的内层 File block_id、`parent_type=docx_file` 与 `replace_file`；云效状态保持不变 |
| 用户明确选择的 HTTPS iframe 不可用 | 保留已审查 HTML，修复托管与 iframe 限制后再发布 |

## 与 `prd` skill 的关系

| 维度 | `prd` skill | `prd-feishu` skill |
|------|------------|---------------------|
| 输出 | 本地 `PRD_xxx.html` 含内联编辑器 | 先交付可操作 `prototype.html`；通过后交付飞书云文档 |
| 原型图 | 内联 HTML 块（含工具栏可编辑） | 已审查 HTML 的页面状态截图，按功能节插入飞书图片块 |
| 彩色徽章 | 内联 CSS 颜色 | 纯文本标注 + 原型图 PNG 内的颜色 |
| 编辑方式 | 浏览器打开 HTML 点编辑 | 从版本文档下载共用原型后操作，PRD 在飞书协同编辑 |
| 适用场景 | 单人写作 / 邮件发送 / 粘贴到语雀 | 团队协同 / 评审 / 长期演进 |

两个 skill **共享 PRD 结构和内容规则**（章节大纲、字段说明表、状态机判定准则、规则要具体等），只在「输出形态」和「原型图呈现方式」上不同。修改 PRD 内容规则时两个 skill 都要同步。
