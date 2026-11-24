try:
    import krita
except ImportError:
    krita = None

if krita is not None:
    from .docker import register_docker

    register_docker()
