# A22 测试与自测说明

本文档用于说明 `F:\服创赛\test` 中训练集、验证集和官方自测包应该如何使用，以及当前系统哪些部分可以自动测试。

## 1. 先明确测试目标

A22 的测试要求实际分为两类：

1. **语音识别模型测试**
   - 官方要求：提供一个 POST API，上传 mp3 二进制文件，返回 JSON：
     ```json
     {"result": "这是一个测试语音。"}
     ```
   - 当前仓库已有 speech-service，但接口是 `/transcribe`，请求体是 JSON + base64 音频，不是官方二进制接口。
   - 所以当前可以先测系统内置 `/transcribe`；如果要完全对齐官方格式，需要再加一个轻量 API 适配层。

2. **数字人面部行为驱动模型测试**
   - 官方评测不直接看 MP4 视频。
   - 核心提交文件是：
     ```text
     prediction_emotion.npy
     ```
   - 形状必须是：
     ```text
     [N, K, T, 25]
     ```
   - 默认通常是 `K=10`、`T=750`、`D=25`。
   - 25 维含义：
     - `0:15`：AU
     - `15:17`：VA
     - `17:25`：EXP
   - 如果当前系统只输出聊天文本、TTS 音频、SoulX MP4 视频，则还不能直接完成官方面部驱动指标评测；必须额外产出 `prediction_emotion.npy`。

## 2. 测试包内容

`F:\服创赛\test` 目前包含：

```text
22-【A22】验证集自测包.rar
23-【A22】维数参数（4月8日新增）.md
A【22】答疑补充说明.md
train.rar
val.rar
```

其中 `22-【A22】验证集自测包.rar` 已确认包含官方自测脚本：

```text
perfrdiff_eval_pack/
  eval_emotion_metrics.py
  person_specific_masked_neighbour_emotion_val.npy
  person_specific_val.csv
  README_eval.md
  requirements_eval.txt
```

## 3. 解压数据

Windows 当前没有检测到 `7z/unrar/rar`，但小的官方自测包可以用 Windows 自带 `tar` 读取。

建议先解压到：

```powershell
mkdir F:\服创赛\test\data
tar -xf "F:\服创赛\test\22-【A22】验证集自测包.rar" -C "F:\服创赛\test"
tar -xf "F:\服创赛\test\train.rar" -C "F:\服创赛\test\data"
tar -xf "F:\服创赛\test\val.rar" -C "F:\服创赛\test\data"
```

如果 `train.rar` 或 `val.rar` 解压失败，安装 7-Zip 后使用：

```powershell
7z x "F:\服创赛\test\train.rar" -o"F:\服创赛\test\data"
7z x "F:\服创赛\test\val.rar" -o"F:\服创赛\test\data"
```

解压后推荐目录结构：

```text
F:\服创赛\test\data\
  train\
    Video_files\
    Audio_files\
    Emotion\
    3D_FV_files\
  val\
    Video_files\
    Audio_files\
    Emotion\
    3D_FV_files\
```

## 4. 数据集结构自动检查

在仓库根目录执行：

```powershell
cd C:\Users\FYF\Documents\GitHub\FuChuangSai_A22
python scripts\evaluation\a22_test_helper.py inspect-data `
  --data-root "F:\服创赛\test\data" `
  --out "F:\服创赛\test\data_inspect_report.json"
```

该命令会检查：

- `train/val` 是否存在。
- `Video_files`、`Audio_files`、`Emotion`、`3D_FV_files` 文件数量。
- `Emotion/*.csv` 样例是否接近 25 维。
- `3D_FV_files/*.npy` 样例形状。

## 5. ASR 自动测试

### 5.1 测当前仓库 speech-service 的 `/transcribe`

如果远端 speech-service 已通过 SSH 隧道映射到本地，例如：

```text
127.0.0.1:19100
```

执行：

```powershell
python scripts\evaluation\a22_test_helper.py asr-batch `
  --mode a22-transcribe-json `
  --url "http://127.0.0.1:19100/transcribe" `
  --audio-dir "F:\服创赛\test\data\val\Audio_files" `
  --glob "*.wav" `
  --limit 20 `
  --out "F:\服创赛\test\asr_transcribe_results.jsonl"
```

### 5.2 测官方二进制 mp3 API

如果后续新增了官方格式接口，例如：

```text
POST http://127.0.0.1:19100/asr
Content-Type: audio/mpeg
Response: {"result": "..."}
```

执行：

```powershell
python scripts\evaluation\a22_test_helper.py asr-batch `
  --mode official-binary `
  --url "http://127.0.0.1:19100/asr" `
  --audio-dir "F:\服创赛\test\data\val\Audio_files" `
  --glob "*.mp3" `
  --limit 20 `
  --out "F:\服创赛\test\asr_official_results.jsonl"
```

## 6. prediction_emotion.npy 输出检查

如果你的面部行为驱动模型已经生成：

```text
F:\服创赛\test\prediction_emotion.npy
```

先检查形状：

```powershell
python scripts\evaluation\a22_test_helper.py check-prediction `
  --prediction "F:\服创赛\test\prediction_emotion.npy" `
  --expected-k 10 `
  --expected-t 750 `
  --expected-d 25 `
  --out "F:\服创赛\test\prediction_check.json"
```

## 7. 官方面部驱动指标自测

安装官方脚本依赖：

```powershell
python -m pip install -r "F:\服创赛\test\perfrdiff_eval_pack\requirements_eval.txt"
```

运行官方自测：

```powershell
python "F:\服创赛\test\perfrdiff_eval_pack\eval_emotion_metrics.py" `
  --data-root "F:\服创赛\test\data" `
  --split val `
  --index-csv "F:\服创赛\test\perfrdiff_eval_pack\person_specific_val.csv" `
  --neighbor-matrix "F:\服创赛\test\perfrdiff_eval_pack\person_specific_masked_neighbour_emotion_val.npy" `
  --prediction "F:\服创赛\test\prediction_emotion.npy" `
  --output-json "F:\服创赛\test\emotion_metrics_result.json"
```

如果只想先快速测不含 DTW 的轻量指标，可指定：

```powershell
python "F:\服创赛\test\perfrdiff_eval_pack\eval_emotion_metrics.py" `
  --data-root "F:\服创赛\test\data" `
  --split val `
  --index-csv "F:\服创赛\test\perfrdiff_eval_pack\person_specific_val.csv" `
  --neighbor-matrix "F:\服创赛\test\perfrdiff_eval_pack\person_specific_masked_neighbour_emotion_val.npy" `
  --prediction "F:\服创赛\test\prediction_emotion.npy" `
  --metrics frdiv,frdvs,frvar `
  --output-json "F:\服创赛\test\emotion_metrics_light_result.json"
```

## 8. 当前系统的测试结论

当前聊天数字人系统可以自动测试：

- 远端服务健康状态。
- 文本聊天接口。
- ASR `/transcribe` 接口。
- TTS 与视频生成链路。
- 前端到远端的端到端交互。

但官方 A22 面部行为驱动评测还需要：

- 按官方验证集样本顺序生成 `prediction_emotion.npy`。
- 保证输出是 `[N, K, T, 25]`。
- 使用官方 `person_specific_val.csv` 和邻居矩阵运行指标。

如果没有 `prediction_emotion.npy`，就无法严肃地计算 FRCorr、FRdist、FRSyn 等官方指标。
