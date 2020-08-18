import os
import pwd
import time
import asyncio
import logging
import docker

from ..schedules import (DataConfigSchedule, DataSettingsSchedule, ParticipantPipelineSchedule, Schedule)
from .base import RunStatus
from .container import (ContainerBackend, ContainerSchedule,
                        ContainerDataSettingsSchedule, ContainerDataConfigSchedule,
                        ContainerParticipantPipelineSchedule)


logger = logging.getLogger(__name__)

docker_statuses = {
    'created': RunStatus.RUNNING,
    'restarting': RunStatus.RUNNING,
    'running': RunStatus.RUNNING,
    'removing': RunStatus.RUNNING,
    'paused': RunStatus.RUNNING,
    'exited': RunStatus.SUCCESS,
    'dead': RunStatus.FAILURE,
}

uid = os.getuid()
gid = pwd.getpwuid(uid).pw_gid

class DockerSchedule(ContainerSchedule):

    _prefix = 'cpacpy-docker_'

    async def _runner(self, command, volumes, port=None):
        container = self.backend.client.containers.run(
            'fcpindi/c-pac:' + self.backend.tag,
            name=f'cpacpy-{repr(self)}',
            command=command,
            detach=True,
            stdin_open=False,
            ports={'8008/tcp': port},
            volumes=volumes,
            user=f'{uid}:{gid}',
        )

        while not container.attrs['NetworkSettings']['Ports']:
            await asyncio.sleep(1)
            container.reload()
        self._run_logs_port = int(container.attrs['NetworkSettings']['Ports']['8008/tcp'][0]['HostPort'])

        while True:
            try:
                await asyncio.sleep(0.5)

                container.reload()
                status = container.status
                if self._run_status == docker_statuses[status]:
                    continue

                self._run_status = docker_statuses[status]
                if status not in ['running', 'created']:
                    break

                if status == 'running':
                    yield {
                        "type": "status",
                        "time": time.time(),
                        "status": RunStatus.RUNNING,
                    }
            except docker.errors.NotFound:
                break

        container.reload()
        status_code = container.attrs['State']['ExitCode']
        dead = container.attrs['State']['Paused'] or container.attrs['State']['OOMKilled'] or container.attrs['State']['Dead']

        self._status = RunStatus.SUCCESS if status_code == 0 and not dead else RunStatus.FAILURE

        yield {
            "type": "status",
            "time": time.time(),
            "status": self._status
        }

        try:
            container.remove(v=True, force=True)
        except:
            pass

class DockerDataSettingsSchedule(ContainerDataSettingsSchedule,
                                 DockerSchedule,
                                 DataSettingsSchedule):
    pass

class DockerDataConfigSchedule(ContainerDataConfigSchedule,
                               DockerSchedule,
                               DataConfigSchedule):
    pass


class DockerParticipantPipelineSchedule(ContainerParticipantPipelineSchedule,
                                        DockerSchedule,
                                        ParticipantPipelineSchedule):
    pass


class DockerBackend(ContainerBackend):

    tag = 'nightly'

    base_schedule_class = DockerSchedule

    schedule_mapping = {
        Schedule: DockerSchedule,
        DataSettingsSchedule: DockerDataSettingsSchedule,
        DataConfigSchedule: DockerDataConfigSchedule,
        ParticipantPipelineSchedule: DockerParticipantPipelineSchedule,
    }

    def __init__(self, scheduler=None, tag=None):
        self.client = docker.from_env()
        try:
            self.client.ping()
        except docker.errors.APIError:
            raise "Could not connect to Docker"

        self.scheduler = scheduler
        self.tag = tag or DockerBackend.tag