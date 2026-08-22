# pix-skill：一张照片，五种独立风格

这里是重新安装后的唯一工作目录。五个 GitHub skill 的项目级安装副本位于 `.agents/skills/`；它们不会安装到 `~/.codex/skills`，也不会在别的项目中自动生效。

原始照片可以放在 `inputs/`；生成物只进入 `outputs/`。

## 使用

从本目录启动 Codex：

```bash
cd /renyuanliu/temp/pix-skill
codex
```

然后发送：

```text
按五种风格处理这张照片：/绝对路径/照片.jpg
```

在已经建立任务上下文后，只发送绝对图片路径也会触发同一流程。完整执行规范见 `WORKFLOW.md`。这不是 Pillow/OpenCV 滤镜脚本：每个结果都必须按对应上游 skill 调用内置图像生成/编辑能力，并分别通过该 skill 的质量检查。

最终结构如下；每个输入照片对应一个带内容哈希的子目录，目录内严格只有五张 PNG：

```text
outputs/
└── <照片名>--<sha256前8位>/
    ├── 01-photo-abstract-editorial.png
    ├── 02-pixel-style-poster-skill.png
    ├── 03-photo-abstract-editorial-skill.png
    ├── 04-gc-minimal-zine-poster.png
    └── 05-photo-relic-editorial.png
```

提示词、生成中间图、验证 manifest 和日志只进入 `.work/`，不会混入成品目录。

## GitHub 来源

版本和校验和锁定在 `UPSTREAMS.lock.json`：

- `photo-abstract-editorial` → `ZzzLc0405/photo-abstract-editorial`，固定提交 `49e5507`。其许可证仅允许个人、教育、研究和非商业用途，并非 OSI 开源许可证。
- `pixel-style-poster-skill` → `v92388375-gif/pixel-style-poster-skill`，固定提交 `b93066b`，MIT。
- `photo-abstract-editorial-skill` → `kwhi6693-web/photo-abstract-editorial` 发布的 `dist/photo-abstract-editorial-skill.zip`，固定提交 `063de8b`，AGPL-3.0；发布 zip 未携带许可证，因此项目另存于 `licenses/photo-abstract-editorial-skill.LICENSE`。
- `gc-minimal-zine-poster` → `LiamGvchi/gc-minimal-zine-poster`，固定提交 `ddb0d66`，MIT。
- `photo-relic-editorial` → `wnby/photo-relic-editorial`，固定提交 `2232da1`，MIT。

第三项发布包内部错误地仍声明 `name: photo-abstract-editorial`，第四项上游声明的是带版本后缀的 `gc-minimal-zine-poster-v0-3`。为了让五个用户指定名称都能唯一调用，安装副本只替换了这两项的 skill 名称及其 `agents/openai.yaml` 中对应的默认调用名；原始内容哈希、安装内容哈希和修改原因均记录在锁文件中，所有生成规则保持上游原样。

## 验证

```bash
python3 scripts/verify_workspace.py
python3 scripts/verify_outputs.py outputs/<照片子目录>
```
