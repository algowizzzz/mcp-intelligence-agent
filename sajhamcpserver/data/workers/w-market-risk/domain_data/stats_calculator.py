"""
Stats Calculator — Sample Python Script
Calculates mean, mode, and median of a given list of numbers.
"""

import statistics


def calculate_stats(numbers):
    """Return mean, median, and mode for the given list."""
    mean = statistics.mean(numbers)
    median = statistics.median(numbers)
    try:
        mode = statistics.mode(numbers)
    except statistics.StatisticsError:
        mode = "No unique mode"
    return mean, median, mode


if __name__ == "__main__":
    data = [12, 7, 3, 14, 6, 14, 8, 11, 14, 3, 5, 9]

    print(f"Input list: {data}")
    print(f"Count:      {len(data)}")
    print()

    mean, median, mode = calculate_stats(data)

    print(f"Mean:       {mean:.2f}")
    print(f"Median:     {median:.2f}")
    print(f"Mode:       {mode}")
