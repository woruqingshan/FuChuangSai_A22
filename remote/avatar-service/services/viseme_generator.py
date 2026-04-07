VISEME_LABELS = ["a", "e", "i", "o", "u", "m", "sil"]


class VisemeGenerator:
    def generate(self, *, text: str, duration_ms: int) -> list[dict]:
        token_count = max(1, min(len(text.strip()) or 1, 6))
        chunk_duration = max(120, duration_ms // token_count)
        visemes = []
        cursor = 0

        for index in range(token_count):
            label = VISEME_LABELS[index % len(VISEME_LABELS)]
            next_cursor = duration_ms if index == token_count - 1 else min(duration_ms, cursor + chunk_duration)
            visemes.append(
                {
                    "start_ms": cursor,
                    "end_ms": next_cursor,
                    "label": label,
                    "weight": round(0.45 + ((index % 3) * 0.1), 2),
                }
            )
            cursor = next_cursor

        return visemes


viseme_generator = VisemeGenerator()
