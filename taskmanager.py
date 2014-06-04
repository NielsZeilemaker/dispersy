from twisted.internet.base import DelayedCall
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall

from .util import blocking_call_on_reactor_thread

CLEANUP_FREQUENCY = 100


class TaskManager(object):
    """
    Provides a set of tools to mantain a list of twisted "tasks" (Deferred, LoopingCall, DelayedCall) that are to be
    executed during the lifetime of an arbitrary object, usually getting killed with it.

    """
    def __init__(self):
        self._pending_tasks = {}
        self._cleanup_counter = CLEANUP_FREQUENCY

    @blocking_call_on_reactor_thread
    def replace_task(self, name, task):
        """
        Replace named task with the new one, cancelling the old one in the process.
        """
        self._maybe_clean_task_list()
        self.cancel_pending_task(name)
        self.register_task(name, task)

    @blocking_call_on_reactor_thread
    def register_task(self, name, task):
        """
        Register a task so it can be canceled at shutdown time or by name.
        """
        assert name not in self._pending_tasks.keys(), name
        assert isinstance(task, (Deferred, DelayedCall, LoopingCall)), task

        self._maybe_clean_task_list()
        self._pending_tasks[name] = task
        return task

    @blocking_call_on_reactor_thread
    def cancel_pending_task(self, name):
        """
        Cancels the named task
        """
        self._maybe_clean_task_list()
        is_active, stopfn = self._get_isactive_stopper(name)
        if is_active:
            stopfn()
            self._pending_tasks.pop(name)


    @blocking_call_on_reactor_thread
    def cancel_all_pending_tasks(self):
        """
        Cancels all the registered tasks.
        This usually should be called when stopping or destroying the object so no tasks are left floating around.
        """
        assert all([isinstance(task, (Deferred, DelayedCall, LoopingCall))
                    for task in self._pending_tasks.itervalues()]), self._pending_tasks

        for name in self._pending_tasks.keys():
            self.cancel_pending_task(name)

    @blocking_call_on_reactor_thread
    def is_pending_task_active(self, name):
        """
        Returns True if the named task is active.
        """
        task = self._pending_tasks.get(name, None)
        if task:
            is_active, _ = self._get_isactive_stopper(task)
            return is_active
        return False

    def _get_isactive_stopper(self, name):
        """
        Return a boolean determining if a task is active and its cancel/stop method.
        """
        task = self._pending_tasks.get(name, None)
        if isinstance(task, Deferred):
            # Have in mind that any deferred in the pending tasks list should have been constructed with a
            # canceller function.
            return not task.called, task.cancel
        elif isinstance(task, DelayedCall):
            return task.active(), task.cancel
        elif isinstance(task, LoopingCall):
            return task.running, task.stop
        else:
            return None, None

    def _maybe_clean_task_list(self):
        """
        Removes finished tasks from the task list.
        """
        if self._cleanup_counter:
            self._cleanup_counter -= 1
        else:
            self._cleaup_counter = CLEANUP_FREQUENCY
            for name in self._pending_tasks.keys():
                if not self.is_pending_task_active(name):
                    self._pending_tasks.pop(name)

__all__ = ["TaskManager"]