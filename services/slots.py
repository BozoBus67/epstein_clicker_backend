import random

def generate_slot_sequence(count: int, length: int, rows: int = 3) -> list[list[int]]:
  return [[random.randint(0, count - 1) for _ in range(length)] for _ in range(rows)]
