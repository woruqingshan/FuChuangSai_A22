import { createAudioTurnRecorder } from "../audio/audioTurnRecorder";
import { VOICE_TURN_STATE } from "../audio/recorderStates";
import { createCameraTurnRecorder } from "../video/cameraTurnRecorder";

export function createInputBar({ onSend, onStatusChange, onVideoStatusChange, onCameraModeChange }) {
  const mediaElement = document.createElement("section");
  mediaElement.className = "capture-panel";
  mediaElement.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">C · Camera</p>
        <h2>Camera Preview</h2>
      </div>
      <span class="chip" data-role="camera-chip">Camera Off</span>
    </div>
    <div class="capture-stage" data-camera-state="disabled">
      <div class="capture-placeholder" data-role="capture-placeholder">
        <p class="capture-title">Camera preview is currently off</p>
        <p class="capture-copy">Enable the camera below to use visual emotion recognition. Text and voice conversations remain available while the camera is off.</p>
      </div>
      <div class="camera-preview-shell hidden" data-role="camera-shell" data-state="disabled">
        <video class="camera-preview camera-preview-large" autoplay muted playsinline></video>
        <div class="camera-preview-overlay" data-role="camera-overlay">Camera Off</div>
      </div>
    </div>
  `;

  const controlsElement = document.createElement("section");
  controlsElement.className = "input-panel compact-input-panel";
  controlsElement.innerHTML = `
    <div class="panel-heading compact-panel-heading">
      <div>
        <p class="eyebrow">C · Input</p>
        <h2>Message</h2>
      </div>
      <span class="chip">Text / Voice / Video</span>
    </div>
    <form class="compact-input-form">
      <div class="compact-compose-row">
        <div class="message-input-shell" data-role="message-input-shell">
          <input id="message-box" class="message-input" type="text" placeholder="Type a message or use voice input." />
          <div class="recording-input-overlay hidden" data-role="recording-input-overlay" aria-live="polite">
            <span class="recording-overlay-text">Recording...</span>
          </div>
        </div>
        <button type="submit" class="primary-button" data-role="send-button">Send</button>
      </div>
      <div class="compact-control-row">
        <button type="button" class="audio-turn-button audio-turn-button-compact" data-role="voice-button" aria-pressed="false">
          <span class="audio-turn-title" data-role="voice-title">Start Voice Input</span>
          <span class="audio-turn-meta" data-role="voice-meta">Click to start recording. Click again to stop and send.</span>
        </button>
        <button type="button" class="secondary-button camera-toggle-button" data-role="camera-toggle">Enable Camera</button>
        <div class="camera-inline-status">
          <p class="camera-inline-title">Camera Status</p>
          <p class="camera-inline-meta" data-role="camera-meta">Camera Off</p>
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
    cameraToggle.textContent = nextEnabled ? "Disable Camera" : "Enable Camera";
    cameraChip.textContent = nextEnabled ? "Camera On" : "Camera Off";
    cameraOverlay.textContent = nextEnabled ? "Live Preview" : "Camera Off";
    onCameraModeChange?.(nextEnabled);
  }

  function syncControls() {
    const textLocked = isBusy || voiceTurnState !== VOICE_TURN_STATE.IDLE;

    messageBox.disabled = textLocked;
    sendButton.disabled = textLocked;
    sendButton.textContent = isBusy ? "Sending..." : "Send";
    // Once captureTurn has returned, the current turn already owns an immutable
    // frame payload. Keep this control available while remote rendering runs so
    // the user can stop the camera without affecting the in-flight turn.
    cameraToggle.disabled = voiceTurnState !== VOICE_TURN_STATE.IDLE;

    voiceButton.disabled = voiceTurnState === VOICE_TURN_STATE.PROCESSING
      || (isBusy && voiceTurnState !== VOICE_TURN_STATE.RECORDING);
    voiceButton.dataset.state = voiceTurnState;
    voiceButton.setAttribute("aria-pressed", String(voiceTurnState === VOICE_TURN_STATE.RECORDING));

    if (voiceTurnState === VOICE_TURN_STATE.RECORDING) {
      voiceTitle.textContent = "Stop Recording";
      voiceMeta.textContent = "Recording. Text input is temporarily locked until this voice turn ends.";
      messageBox.placeholder = "Recording... This turn will be sent as voice.";
      setRecordingOverlay(true);
      return;
    }

    if (voiceTurnState === VOICE_TURN_STATE.PROCESSING) {
      voiceTitle.textContent = "Processing Voice";
      voiceMeta.textContent = "Preparing the recording and sending it to the local service.";
      messageBox.placeholder = "Processing voice input...";
      setRecordingOverlay(false);
      return;
    }

    voiceTitle.textContent = "Start Voice Input";
    voiceMeta.textContent = "Use your microphone for a voice interaction. Click again to stop and send.";
    messageBox.placeholder = "Type a message or use voice input.";
    setRecordingOverlay(false);
  }

  function setCameraMeta(text) {
    cameraMeta.textContent = text;
  }

  async function captureOptionalVideoTurn(baseTurnWindow = null) {
    if (!cameraRecorder.isEnabled()) {
      return null;
    }

    onVideoStatusChange("Capturing camera frames for this turn.");

    try {
      const payload = await cameraRecorder.captureTurn(baseTurnWindow);

      if (payload?.video_frames?.length) {
        const count = payload.video_frames.length;
        setCameraMeta(`${count} frames attached`);
        onVideoStatusChange(`${count} camera frames attached`);
      } else {
        setCameraMeta("No frames attached");
        onVideoStatusChange("The camera is on, but no video frames were attached to this turn.");
      }

      return payload;
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Camera capture failed.";
      setCameraMeta("Capture skipped");
      onVideoStatusChange(`Camera capture is unavailable for this turn: ${detail}`);
      onStatusChange(`Camera capture was skipped for this turn: ${detail}`);
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
      onStatusChange("Recording through the microphone. Text input is temporarily unavailable.");
    } catch (error) {
      voiceTurnState = VOICE_TURN_STATE.IDLE;
      messageBox.value = preservedDraft;
      preservedDraft = "";
      syncControls();

      const detail = error instanceof Error ? error.message : "Voice capture failed.";
      onStatusChange(detail);
    }
  }

  async function stopVoiceTurn() {
    voiceTurnState = VOICE_TURN_STATE.PROCESSING;
    syncControls();
    onStatusChange("Stopping the recording and preparing to send.");

    try {
      const audioPayload = await recorder.stop();
      if (!audioPayload?.audio_base64) {
        throw new Error("No voice content was recorded for this turn.");
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

      const detail = error instanceof Error ? error.message : "Voice processing failed.";
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
        setCameraMeta("Live Preview");
        onVideoStatusChange("Camera Preview On");
        return;
      }

      await cameraRecorder.disable();
      setCameraPresentation(false);
      setCameraMeta("Camera Off");
      onVideoStatusChange("Camera Off");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Camera capture failed.";
      setCameraPresentation(false);
      setCameraMeta("Camera Error");
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
      onStatusChange("Input cleared. You can continue the conversation.");
    }
  });

  setCameraPresentation(false);
  setCameraMeta("Camera Off");
  onVideoStatusChange("Camera Off");
  syncControls();

  return {
    mediaElement,
    controlsElement,
    setBusy,
  };
}
