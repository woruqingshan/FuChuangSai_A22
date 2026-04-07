export function applyExpressionSequence(faceElement, sequence, fallbackExpression) {
  const timers = [];
  faceElement.dataset.expression = fallbackExpression || "neutral";

  if (!sequence?.length) {
    return () => {
      faceElement.dataset.expression = fallbackExpression || "neutral";
    };
  }

  sequence.forEach((cue) => {
    const timerId = window.setTimeout(() => {
      faceElement.dataset.expression = cue.expression || fallbackExpression || "neutral";
    }, cue.start_ms || 0);
    timers.push(timerId);
  });

  return () => {
    timers.forEach((timerId) => window.clearTimeout(timerId));
    faceElement.dataset.expression = fallbackExpression || "neutral";
  };
}
