import functools

# --- Implementation 1: Single Dispatch (The 'Pythonic' Overloading) ---
# This allows the function to behave differently based on the TYPE of the 
# first argument.

@functools.singledispatch
def process_data(data):
    """The base implementation for unknown types."""
    print(f"Generic processing: {data}")

@process_data.register(int)
def _(data):
    """Implementation specifically for integers."""
    print(f"Integer math processing: {data * 10}")

@process_data.register(list)
def _(data):
    """Implementation specifically for lists."""
    print(f"List iteration processing: {', '.join(map(str, data))}")
    



if __name__ == "__main__":
    # Testing Single Dispatch
    process_data("hi")
    process_data(5)           # Calls int version
    process_data([1, 2, 3])   # Calls list version
    