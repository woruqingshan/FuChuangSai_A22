async function blobToBase64(blob) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Audio conversion failed."));
        return;
      }
      resolve(result.split(",")[1] || "");
    };
    reader.onerror = () => reject(new Error("Audio conversion failed."));
    reader.readAsDataURL(blob);
  });
}

function simplifyAudioFormat(mimeType) {
  if (mimeType.includes("webm")) {
    return "webm";
  }
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  if (mimeType.includes("wav")) {
    return "wav";
  }
  return "unknown";
}

export function createInputBar({ onSend, onStatusChange }) {
  const element = document.createElement("section");
  element.className = "input-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">C · Input</p>
        <h2>Text / Audio Entry</h2>
      </div>
      <span class="chip">Audio-first scaffold</span>
    </div>
    <form class="input-form">
      <label class="field-label" for="message-box">Text message</label>
      <textarea id="message-box" rows="5" placeholder="Type a supportive conversation prompt or record audio."></textarea>
      <div class="input-actions">
        <button type="button" class="secondary-button" data-role="record-button">Start audio capture</button>
        <button type="submit" class="primary-button" data-role="send-button">Send turn</button>
      </div>
      <div class="audio-attachment" data-role="audio-attachment">No audio attached.</div>
    </form>
  `;

  const form = element.querySelector(".input-form");
  const messageBox = element.querySelector("#message-box");
  const recordButton = element.querySelector('[data-role="record-button"]');
  const sendButton = element.querySelector('[data-role="send-button"]');
  const attachment = element.querySelector('[data-role="audio-attachment"]');

  let mediaRecorder = null;
  let mediaStream = null;
  let chunks = [];
  let recordingStartedAt = 0;
  let pendingAudio = null;
  let isRecording = false;

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onStatusChange("Audio capture is not supported in this browser.");
      return;
    }

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(mediaStream);
    chunks = [];
    recordingStartedAt = Date.now();
    isRecording = true;

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener("stop", async () => {
      const mimeType = mediaRecorder.mimeType || "audio/webm";
      const blob = new Blob(chunks, { type: mimeType });
      pendingAudio = {
        audio_base64: await blobToBase64(blob),
        audio_format: simplifyAudioFormat(mimeType),
        audio_duration_ms: Date.now() - recordingStartedAt,
      };
      attachment.textContent = `Audio attached: ${pendingAudio.audio_format} · ${pendingAudio.audio_duration_ms} ms`;
      onStatusChange("Audio clip attached and ready to send.");
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    });

    mediaRecorder.start();
    recordButton.textContent = "Stop audio capture";
    attachment.textContent = "Recording audio...";
    onStatusChange("Recording audio from microphone.");
  }

  function stopRecording() {
    if (!mediaRecorder || !isRecording) {
      return;
    }

    isRecording = false;
    mediaRecorder.stop();
    recordButton.textContent = "Start audio capture";
  }

  function setBusy(isBusy) {
    messageBox.disabled = isBusy;
    recordButton.disabled = isBusy;
    sendButton.disabled = isBusy;
    sendButton.textContent = isBusy ? "Sending..." : "Send turn";
  }

  recordButton.addEventListener("click", async () => {
    try {
      if (isRecording) {
        stopRecording();
      } else {
        await startRecording();
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Audio capture failed.";
      attachment.textContent = detail;
      onStatusChange(detail);
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
      }
      recordButton.textContent = "Start audio capture";
      isRecording = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const sent = await onSend({
      text: messageBox.value.trim(),
      audio: pendingAudio,
    });
    if (sent) {
      messageBox.value = "";
      pendingAudio = null;
      attachment.textContent = "No audio attached.";
      onStatusChange("Input cleared and ready for the next turn.");
    }
  });

  return {
    element,
    setBusy,
  };
}
