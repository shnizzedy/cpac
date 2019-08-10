from .docker import Docker, DockerDataSettingsSchedule


class BackendMapper(object):

    parameters = {}

    def __init__(self, **kwargs):
        self.parameters = kwargs



class DataSettingsSchedule(BackendMapper):

    _clients = {
        Docker: DockerDataSettingsSchedule
    }

    def __call__(self, backend, parent=None):
        return self._clients[backend.__class__](
            backend=backend,
            **self.parameters,
            parent=parent
        )


