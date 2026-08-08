def pearson_r(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation coefficient. None if fewer than 2 points or zero variance in either series."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    if var_x == 0 or var_y == 0:
        return None

    return cov / (var_x**0.5 * var_y**0.5)
