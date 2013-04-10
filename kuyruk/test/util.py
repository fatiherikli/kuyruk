import sys
import logging
import subprocess
from time import sleep
from functools import partial
from contextlib import contextmanager

import pexpect

from ..connection import LazyConnection
from ..queue import Queue as RabbitQueue

logger = logging.getLogger(__name__)


def delete_queue(*queues):
    """Delete queues from RabbitMQ"""
    conn = LazyConnection()
    ch = conn.channel()
    with conn:
        with ch:
            for name in queues:
                RabbitQueue(name, ch).delete()


def is_empty(queue):
    queue = RabbitQueue(queue, LazyConnection().channel())
    return len(queue) == 0


@contextmanager
def run_kuyruk(queues='kuyruk'):
    child = pexpect.spawn(sys.executable, [
        '-m', 'kuyruk.__main__',  # run main module
        '--queues', queues,
    ], timeout=10)
    yield child
    child.terminate(force=True)
    sleep_while(partial(get_pids, 'kuyruk:'))


def kill_worker():
    pexpect.run("pkill -9 -f 'kuyruk: worker'")


def get_pids(pattern):
    logger.debug('get_pids: %s', pattern)
    cmd = "pgrep -fl '%s'" % pattern
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    out = p.communicate()[0]
    logger.debug("\n%s", out)
    lines = out.splitlines()
    # filter pgrep itself. travis runs it like: "/bin/sh -c pgrep -fl 'kuyruk:'"
    lines = filter(lambda x: not cmd in x, lines)
    pids = [int(l.split()[0]) for l in lines]  # take first column
    logger.debug('pids: %s', pids)
    return pids


def get_pid(pattern):
    pids = get_pids(pattern)
    assert len(pids) == 1
    return pids[0]


def sleep_while(f):
    while f():
        sleep(0.1)
