export function applyMotionSequence(faceElement, sequence, fallbackMotion) {
  const timers = [];
  faceElement.dataset.motion = fallbackMotion || "steady";

  if (!sequence?.length) {
    return () => {
      faceElement.dataset.motion = fallbackMotion || "steady";
    };
  }

  sequence.forEach((cue) => {
    const timerId = window.setTimeout(() => {
      faceElement.dataset.motion = cue.motion || fallbackMotion || "steady";
    }, cue.start_ms || 0);
    timers.push(timerId);
  });

  return () => {
    timers.forEach((timerId) => window.clearTimeout(timerId));
    faceElement.dataset.motion = fallbackMotion || "steady";
  };
}
