FUNCTION_REGISTRY = {}

def register(name=None):
    def wrapper(func):
        FUNCTION_REGISTRY[f"{name}.{func.__name__}"] = func
        return func
    return wrapper