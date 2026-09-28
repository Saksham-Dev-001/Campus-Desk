from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
login_manager = LoginManager()
csrf = CSRFProtect()

try:
    from flask_caching import Cache
    cache = Cache()
except ImportError:
    class DummyCache:
        """In-memory fallback cache when flask_caching is not installed."""
        def __init__(self, *args, **kwargs):
            self._storage = {}

        def init_app(self, app, config=None):
            pass

        def get(self, key):
            return self._storage.get(key)

        def set(self, key, value, timeout=None):
            self._storage[key] = value
            return True

        def delete(self, key):
            self._storage.pop(key, None)
            return True

        def clear(self):
            self._storage.clear()
            return True

        def cached(self, timeout=None, key_prefix='view/%s', unless=None):
            def decorator(f):
                return f
            return decorator

    cache = DummyCache()

