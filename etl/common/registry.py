FUNCTION_REGISTRY = {}

def register(name=None):
    def wrapper(func):
        FUNCTION_REGISTRY[name or func.__name__] = func
        return func
    return wrapper