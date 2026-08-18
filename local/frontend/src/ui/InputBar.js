import { createAudioTurnRecorder } from "../audio/audioTurnRecorder";
import { VOICE_TURN_STATE } from "../audio/recorderStates";
import { createCameraTurnRecorder } from "../video/cameraTurnRecorder";

export function createInputBar({ onSend, onStatusChange, onVideoStatusChange, onCameraModeChange }) {
  const mediaElement = document.createElement("section");
  mediaElement.className = "capture-panel";
  mediaElement.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">C · 摄像头</p>
        <h2>摄像头预览</h2>
      </div>
      <span class="chip" data-role="camera-chip">摄像头待开启</span>
    </div>
    <div class="capture-stage" data-camera-state="disabled">
      <div class="capture-placeholder" data-role="capture-placeholder">
        <p class="capture-title">摄像头预览当前已关闭</p>
        <p class="capture-copy">如需使用视频情绪识别，可点击下方按钮开启摄像头。不使用摄像头时，文字和语音对话仍可正常使用。</p>
      </div>
      <div class="camera-preview-shell hidden" data-role="camera-shell" data-state="disabled">
        <video class="camera-preview camera-preview-large" autoplay muted playsinline></video>
        <div class="camera-preview-overlay" data-role="camera-overlay">摄像头已关闭</div>
      </div>
    </div>
  `;

  const controlsElement = document.createElement("section");
  controlsElement.className = "input-panel compact-input-panel";
  controlsElement.innerHTML = `
    <div class="panel-heading compact-panel-heading">
      <div>
        <p class="eyebrow">C · 输入</p>
        <h2>对话输入</h2>
      </div>
      <span class="chip">文字 / 语音 / 视频</span>
    </div>
    <form class="compact-input-form">
      <div class="compact-compose-row">
        <div class="message-input-shell" data-role="message-input-shell">
          <input id="message-box" class="message-input" type="text" placeholder="请输入想说的话，或点击语音按钮。" />
          <div class="recording-input-overlay hidden" data-role="recording-input-overlay" aria-live="polite">
            <span class="recording-overlay-text">正在录音中</span>
          </div>
        </div>
        <button type="submit" class="primary-button" data-role="send-button">发送</button>
      </div>
      <div class="compact-control-row">
        <button type="button" class="audio-turn-button audio-turn-button-compact" data-role="voice-button" aria-pressed="false">
          <span class="audio-turn-title" data-role="voice-title">开始语音输入</span>
          <span class="audio-turn-meta" data-role="voice-meta">点击开始录音，再次点击停止并发送。</span>
        </button>
        <button type="button" class="secondary-button camera-toggle-button" data-role="camera-toggle">开启摄像头</button>
        <div class="camera-inline-status">
          <p class="camera-inline-title">视频采集状态</p>
          <p class="camera-inline-meta" data-role="camera-meta">摄像头已关闭，本轮不会附带视频画面。</p>
        </div>
      </div>
    </form>
  `;

  const form = controlsElement.querySelector(".compact-input-form");
  const messageInputShell = controlsElement.querySelector('[data-role="message-input-shell"]');
  const messageBox = controlsElement.querySelector("#message-box");
  const recordingInputOverlay = controlsElement.querySelector('[data-role="recording-input-overlay"]');
  const sendButton = controlsElement.querySelector('[data-role="send-button"]');
  const voiceButton = controlsElement.querySelector('[data-role="voice-button"]');
  const voiceTitle = controlsElement.querySelector('[data-role="voice-title"]');
  const voiceMeta = controlsElement.querySelector('[data-role="voice-meta"]');
  const cameraToggle = controlsElement.querySelector('[data-role="camera-toggle"]');
  const cameraMeta = controlsElement.querySelector('[data-role="camera-meta"]');
  const cameraChip = mediaElement.querySelector('[data-role="camera-chip"]');
  const captureStage = mediaElement.querySelector(".capture-stage");
  const capturePlaceholder = mediaElement.querySelector('[data-role="capture-placeholder"]');
  const cameraShell = mediaElement.querySelector('[data-role="camera-shell"]');
  const cameraOverlay = mediaElement.querySelector('[data-role="camera-overlay"]');
  const cameraPreview = mediaElement.querySelector(".camera-preview");

  const recorder = createAudioTurnRecorder();
  const cameraRecorder = createCameraTurnRecorder();
  cameraRecorder.bindPreview(cameraPreview);

  let isBusy = false;
  let voiceTurnState = VOICE_TURN_STATE.IDLE;
  let preservedDraft = "";
  let cameraEnabled = false;

  function setRecordingOverlay(visible) {
    messageInputShell.dataset.recording = visible ? "on" : "off";
    recordingInputOverlay.classList.toggle("hidden", !visible);
  }

  function setCameraPresentation(nextEnabled) {
    cameraEnabled = nextEnabled;
    captureStage.dataset.cameraState = nextEnabled ? "enabled" : "disabled";
    cameraShell.dataset.state = nextEnabled ? "enabled" : "disabled";
    cameraShell.classList.toggle("hidden", !nextEnabled);
    capturePlaceholder.classList.toggle("hidden", nextEnabled);
    cameraToggle.textContent = nextEnabled ? "关闭摄像头" : "开启摄像头";
    cameraChip.textContent = nextEnabled ? "摄像头已开启" : "摄像头待开启";
    cameraOverlay.textContent = nextEnabled ? "实时预览中" : "摄像头已关闭";
    onCameraModeChange?.(nextEnabled);
  }

  function syncControls() {
    const textLocked = isBusy || voiceTurnState !== VOICE_TURN_STATE.IDLE;

    messageBox.disabled = textLocked;
    sendButton.disabled = textLocked;
    sendButton.textContent = isBusy ? "发送中..." : "发送";
    // Once captureTurn has returned, the current turn already owns an immutable
    // frame payload. Keep this control available while remote rendering runs so
    // the user can stop the camera without affecting the in-flight turn.
    cameraToggle.disabled = voiceTurnState !== VOICE_TURN_STATE.IDLE;

    voiceButton.disabled = voiceTurnState === VOICE_TURN_STATE.PROCESSING
      || (isBusy && voiceTurnState !== VOICE_TURN_STATE.RECORDING);
    voiceButton.dataset.state = voiceTurnState;
    voiceButton.setAttribute("aria-pressed", String(voiceTurnState === VOICE_TURN_STATE.RECORDING));

    if (voiceTurnState === VOICE_TURN_STATE.RECORDING) {
      voiceTitle.textContent = "停止语音输入";
      voiceMeta.textContent = "正在录音。本轮语音结束前，文字输入会暂时锁定。";
      messageBox.placeholder = "正在录音中，本轮将以语音发送。";
      setRecordingOverlay(true);
      return;
    }

    if (voiceTurnState === VOICE_TURN_STATE.PROCESSING) {
      voiceTitle.textContent = "正在处理语音";
      voiceMeta.textContent = "正在整理录音并发送到本地服务。";
      messageBox.placeholder = "正在处理语音输入...";
      setRecordingOverlay(false);
      return;
    }

    voiceTitle.textContent = "开始语音输入";
    voiceMeta.textContent = "使用麦克风进行一轮语音对话。再次点击即可停止并发送。";
    messageBox.placeholder = "请输入想说的话，或点击语音按钮。";
    setRecordingOverlay(false);
  }

  function setCameraMeta(text) {
    cameraMeta.textContent = text;
  }

  async function captureOptionalVideoTurn(baseTurnWindow = null) {
    if (!cameraRecorder.isEnabled()) {
      return null;
    }

    onVideoStatusChange("正在采集本轮摄像头画面。");

    try {
      const payload = await cameraRecorder.captureTurn(baseTurnWindow);

      if (payload?.video_frames?.length) {
        const count = payload.video_frames.length;
        const preRollMs = payload.turn_time_window?.pre_roll_ms || 0;
        const postRollMs = payload.turn_time_window?.post_roll_ms || 0;
        setCameraMeta(
          `摄像头已开启，已附带 ${count} 帧关键画面（前置缓存 ${preRollMs} 毫秒，后置缓存 ${postRollMs} 毫秒）。`,
        );
        onVideoStatusChange(`已附带 ${count} 帧摄像头画面`);
      } else {
        setCameraMeta("摄像头已开启，但本轮未附带视频画面。");
        onVideoStatusChange("摄像头已开启，但本轮未附带视频画面。");
      }

      return payload;
    } catch (error) {
      const detail = error instanceof Error ? error.message : "摄像头采集失败。";
      setCameraMeta(`摄像头已开启，但本轮将只使用语音或文字。${detail}`);
      onVideoStatusChange(`本轮摄像头采集不可用：${detail}`);
      onStatusChange(`本轮已跳过摄像头采集：${detail}`);
      return null;
    }
  }

  async function startVoiceTurn() {
    preservedDraft = messageBox.value;
    voiceTurnState = VOICE_TURN_STATE.RECORDING;
    messageBox.value = "";
    syncControls();

    try {
      await recorder.start();
      onStatusChange("正在通过麦克风录音，本轮暂时不能输入文字。");
    } catch (error) {
      voiceTurnState = VOICE_TURN_STATE.IDLE;
      messageBox.value = preservedDraft;
      preservedDraft = "";
      syncControls();

      const detail = error instanceof Error ? error.message : "语音采集失败。";
      onStatusChange(detail);
    }
  }

  async function stopVoiceTurn() {
    voiceTurnState = VOICE_TURN_STATE.PROCESSING;
    syncControls();
    onStatusChange("正在停止录音并准备发送。");

    try {
      const audioPayload = await recorder.stop();
      if (!audioPayload?.audio_base64) {
        throw new Error("本轮没有录到语音内容。");
      }

      const videoPayload = await captureOptionalVideoTurn(audioPayload.turn_time_window);
      const sent = await onSend({
        text: "",
        audio: audioPayload,
        video: videoPayload,
      });

      if (!sent) {
        messageBox.value = preservedDraft;
      }

      preservedDraft = "";
    } catch (error) {
      messageBox.value = preservedDraft;
      preservedDraft = "";

      const detail = error instanceof Error ? error.message : "语音处理失败。";
      onStatusChange(detail);
    } finally {
      voiceTurnState = VOICE_TURN_STATE.IDLE;
      syncControls();
    }
  }

  function setBusy(nextBusy) {
    isBusy = nextBusy;
    syncControls();
  }

  cameraToggle.addEventListener("click", async () => {
    if (cameraToggle.disabled) {
      return;
    }

    try {
      if (!cameraEnabled) {
        await cameraRecorder.enable();
        setCameraPresentation(true);
        setCameraMeta("摄像头预览已开启，系统会自动缓存最近画面用于本轮分析。");
        onVideoStatusChange("摄像头预览已开启");
        return;
      }

      await cameraRecorder.disable();
      setCameraPresentation(false);
      setCameraMeta("摄像头已关闭；已发送轮次不受影响，下一轮不会附带视频画面。");
      onVideoStatusChange("摄像头未开启");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "摄像头采集失败。";
      setCameraPresentation(false);
      setCameraMeta(detail);
      onVideoStatusChange(detail);
      onStatusChange(detail);
    }
  });

  voiceButton.addEventListener("click", async () => {
    if (voiceTurnState === VOICE_TURN_STATE.RECORDING) {
      await stopVoiceTurn();
      return;
    }

    if (voiceTurnState === VOICE_TURN_STATE.IDLE) {
      await startVoiceTurn();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const videoPayload = await captureOptionalVideoTurn();
    const sent = await onSend({
      text: messageBox.value.trim(),
      audio: null,
      video: videoPayload,
    });
    if (sent) {
      messageBox.value = "";
      onStatusChange("输入已清空，可以继续对话。");
    }
  });

  setCameraPresentation(false);
  setCameraMeta("摄像头已关闭，本轮不会附带视频画面。");
  onVideoStatusChange("摄像头未开启");
  syncControls();

  return {
    mediaElement,
    controlsElement,
    setBusy,
  };
}
