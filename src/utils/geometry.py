# src/utils/geometry.py


class Rect:
    """A simple rectangle class for x, y, width, height."""

    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __repr__(self):
        return f"Rect(x={self.x}, y={self.y}, w={self.w}, h={self.h})"

    def to_tuple(self):
        return (self.x, self.y, self.w, self.h)


# Other geometry-related utilities can be added here,
# e.g., functions for collision detection, coordinate transformations, etc.
