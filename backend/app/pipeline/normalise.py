"""Case-fold and collapse whitespace while retaining source offsets."""
from dataclasses import dataclass

@dataclass(frozen=True)
class NormalisedText:
    text: str
    start_map: tuple[int, ...]
    end_map: tuple[int, ...]

def normalise_with_offsets(value: str) -> NormalisedText:
    output: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    index = 0
    while index < len(value):
        if value[index].isspace():
            run_start = index
            index += 1
            while index < len(value) and value[index].isspace():
                index += 1
            output.append(" ")
            starts.append(run_start)
            ends.append(index)
            continue
        folded = value[index].casefold()
        for char in folded:
            output.append(char)
            starts.append(index)
            ends.append(index + 1)
        index += 1
    return NormalisedText("".join(output), tuple(starts), tuple(ends))

def original_span(normalised: NormalisedText, start: int, end: int) -> tuple[int, int]:
    if start < 0 or end > len(normalised.text) or start >= end:
        raise ValueError("Expected a valid non-empty normalised span")
    return normalised.start_map[start], normalised.end_map[end - 1]

def normalise(value: str) -> str:
    return normalise_with_offsets(value).text
