import os
import pandas as pd
import pwd
import tempfile
import textwrap

from collections import namedtuple
from tabulate import tabulate

from cpac.utils import Locals_to_bind, Permission_mode


Platform_Meta = namedtuple('Platform_Meta', 'name symbol')


class Backend(object):
    def __init__(self):
        pass  # pragma: no cover

    def start(self, pipeline_config, subject_config):
        raise NotImplementedError()

    def _bind_volume(self, local, remote, mode):
        local, remote = self._prep_binding(local, remote)
        b = {'bind': remote, 'mode': Permission_mode(mode)}
        if local in self.volumes:
            if remote in [binding['bind'] for binding in self.volumes[local]]:
                for i, binding in enumerate(self.volumes[local]):
                    self.volumes[local][i] = {
                        'bind': remote,
                        'mode': max([
                            self.volumes[local][i]['mode'], b['mode']
                        ])
                    }
            else:
                self.volumes[local].append(b)
        else:
            self.volumes[local] = [b]

    def _load_logging(self, image):
        t = pd.DataFrame([
            (i, j['bind'], j['mode']) for i in self.bindings['volumes'].keys(
            ) for j in self.bindings['volumes'][i]
        ])
        t.columns = ['local', self.platform.name, 'mode']
        print(" ".join([
            f"Loading {self.platform.symbol}",
            image,
            "with these directory bindings:"
        ]))
        print(textwrap.indent(
            tabulate(t.applymap(
                lambda x: (
                    '\n'.join(textwrap.wrap(x, 42))
                ) if isinstance(x, str) else x
            ), headers='keys', showindex=False),
            '  '
        ))
        print(f"Logging messages will refer to the {self.platform.name} paths.\n")

    def _prep_binding(self, binding_path_local, binding_path_remote):
        binding_path_local = os.path.abspath(
            os.path.expanduser(binding_path_local)
        )
        os.makedirs(binding_path_local, exist_ok=True)
        return(
            os.path.realpath(binding_path_local),
            os.path.abspath(binding_path_remote)
        )

    def _set_bindings(self, **kwargs):
        tag = kwargs.get('tag', None)
        tag = tag if isinstance(tag, str) else None

        temp_dir = kwargs.get(
            'temp_dir',
            tempfile.mkdtemp(prefix='cpac_pip_temp_')
        )
        output_dir = kwargs.get(
            'output_dir',
            tempfile.mkdtemp(prefix='cpac_pip_output_')
        )
        working_dir = kwargs.get(
            'working_dir',
            os.getcwd()
        )


        for kwarg in [
            *kwargs.get('extra_args', []), kwargs.get('crashfile', '')
        ]:
            if os.path.exists(kwarg):
                d = kwarg if os.path.isdir(kwarg) else os.path.dirname(kwarg)
                self._bind_volume(d, d, 'r')
        if 'data_config_file' in kwargs and isinstance(
            kwargs['data_config_file'], str
        ) and os.path.exists(kwargs['data_config_file']):
            dc_dir = os.path.dirname(kwargs['data_config_file'])
            self._bind_volume(dc_dir, dc_dir, 'r')
            locals_from_data_config = Locals_to_bind()
            locals_from_data_config.from_config_file(
                kwargs['data_config_file']
            )
            for local in locals_from_data_config.locals:
                self._bind_volume(local, local, 'r')
        self._bind_volume(temp_dir, temp_dir, 'rw')
        self._bind_volume(output_dir, output_dir, 'rw')
        self._bind_volume(working_dir, working_dir, 'rw')
        if kwargs.get('custom_binding'):
            for d in kwargs['custom_binding']:
                self._bind_volume(*d.split(':'), 'r')
        for d in ['bids_dir', 'output_dir']:
            if d in kwargs and isinstance(kwargs[d], str) and os.path.exists(
                kwargs[d]
            ):
                self._bind_volume(
                    kwargs[d],
                    kwargs[d],
                    'rw' if d == 'output_dir' else 'r'
                )

        uid = os.getuid()

        self.bindings = {
            'gid': pwd.getpwuid(uid).pw_gid,
            'mounts': [
                '{}:{}:{}'.format(
                    i,
                    j['bind'],
                    j['mode']
                ) for i in self.volumes.keys() for j in self.volumes[i]
            ],
            'tag': tag,
            'uid': uid,
            'volumes': self.volumes
        }


class Result(object):

    mime = None

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self):
        yield self.value

    @property
    def description(self):
        return {
            'type': 'object'
        }


class FileResult(Result):

    def __init__(self, name, value, mime):
        self.name = name
        self.value = value
        self.mime = mime

    def __call__(self):
        with open(self.value, 'rb') as f:
            while True:
                piece = f.read(1024)
                if piece:
                    yield piece
                else:
                    return

    @property
    def description(self):
        return {
            'type': 'file',
            'mime': self.mime
        }
