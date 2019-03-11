class MockBackend:
    def __init__(self):
        self.__version__ = '0.1-mock'

def load_backend(**kwargs):
    return MockBackend()
