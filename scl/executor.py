from rclpy.executors import Executor, ShutdownException, TimeoutException
from rclpy.context import Context
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

#haya
import os 
#woo
import time
from typing import List
from typing import Callable
from typing import Generator
from typing import Tuple
from rclpy.task import Task
from rclpy.waitable import Waitable
from rclpy.waitable import NumberOfEntities
from typing import TypeVar
from rclpy.utilities import timeout_sec_to_nsec
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from contextlib import ExitStack
from typing import Set
from rclpy.node import Node
WaitableEntityType = TypeVar('WaitableEntityType')

from rclpy.client import Client
from rclpy.clock import Clock
from rclpy.clock import ClockType
from rclpy.context import Context
from rclpy.guard_condition import GuardCondition
from rclpy.handle import InvalidHandle
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from rclpy.service import Service
from rclpy.signals import SignalHandlerGuardCondition
from rclpy.subscription import Subscription
from rclpy.task import Future
from rclpy.task import Task
from rclpy.timer import WallTimer
from rclpy.utilities import get_default_context
from rclpy.utilities import timeout_sec_to_nsec
from rclpy.waitable import NumberOfEntities
from rclpy.waitable import Waitable

from scl.ports import StreamInputPort, EventInputPort, ModeChangePort
from scl.components import Component

class SplashExecutor(Executor):
    def __init__(self, num_threads: int = None, *, context: Context = None) -> None:
        super().__init__(context=context)
        if num_threads is None:
            try:
                num_threads = multiprocessing.cpu_count()
            except NotImplementedError:
                print("thread is 1")
                num_threads = 1
        self._executor = ThreadPoolExecutor(num_threads)

    def spin_once(self, timeout_sec: float = None) -> None:
        try:
            handler, entity, node = self.wait_for_ready_callbacks(timeout_sec=timeout_sec)
        except ShutdownException:
            pass
        except TimeoutException:
            pass
        else:
            self._executor.submit(handler)

    def wait_for_ready_callbacks(self, *args, **kwargs) -> Tuple[Task, WaitableEntityType, 'Node']:
        """
        Return callbacks that are ready to be executed.

        The arguments to this function are passed to the internal method
        :meth:`_wait_for_ready_callbacks` to get a generator for ready callbacks:

        .. Including the docstring for the hidden function for reference
        .. automethod:: _wait_for_ready_callbacks
        """
        while True:
            if self._cb_iter is None or self._last_args != args or self._last_kwargs != kwargs:
                # Create a new generator
                self._last_args = args
                self._last_kwargs = kwargs
                self._cb_iter = self._wait_for_ready_callbacks(*args, **kwargs)

            try:
                return next(self._cb_iter)
            except StopIteration:
                # Generator ran out of work
                self._cb_iter = None

    def get_active_nodes(self) -> List['Node']:
        with self._nodes_lock:
            active_nodes = []
            for node in self._nodes:
                if isinstance(node, Component):
                    if node.is_active:
                        active_nodes.append(node)
                    else:
                        continue
                else:
                    active_nodes.append(node)
            return list(active_nodes)
    
    def _wait_for_ready_callbacks(
        self,
        timeout_sec: float = None,
        nodes: List['Node'] = None,
        condition: Callable[[], bool] = lambda: False,
    ) -> Generator[Tuple[Task, WaitableEntityType, 'Node'], None, None]:
        """
        Yield callbacks that are ready to be executed.

        :raise TimeoutException: on timeout.
        :raise ShutdownException: on if executor was shut down.

        :param timeout_sec: Seconds to wait. Block forever if ``None`` or negative.
            Don't wait if 0.
        :param nodes: A list of nodes to wait on. Wait on all nodes if ``None``.
        :param condition: A callable that makes the function return immediately when it evaluates
            to True.
        """
        timeout_timer = None
        timeout_nsec = timeout_sec_to_nsec(timeout_sec)
        # timeout_nsec = timeout_sec_to_nsec(1) #haya
        # print("timeout_sec", timeout_sec)
        # print("timeout_nsec", timeout_nsec)
        if timeout_nsec > 0:
            timeout_timer = WallTimer(None, None, timeout_nsec, self._clock, context=self._context)

        yielded_work = False
        while not yielded_work and not self._is_shutdown and not condition():
            # Refresh "all" nodes in case executor was woken by a node being added or removed
            nodes_to_use = nodes
            if nodes is None:
                # nodes_to_use = self.get_nodes()
                nodes_to_use = self.get_active_nodes()

            # Yield tasks in-progress before waiting for new work
            tasks = None
            with self._tasks_lock:
                tasks = list(self._tasks)
            if tasks:
                for task, entity, node in reversed(tasks):
                    if (not task.executing() and not task.done() and
                            (node is None or node in nodes_to_use)):
                        yielded_work = True
                        yield task, entity, node
                with self._tasks_lock:
                    # Get rid of any tasks that are done
                    self._tasks = list(filter(lambda t_e_n: not t_e_n[0].done(), self._tasks))

            # Gather entities that can be waited on
            subscriptions: List[Subscription] = []
            guards: List[GuardCondition] = []
            timers: List[WallTimer] = []
            clients: List[Client] = []
            services: List[Service] = []
            waitables: List[Waitable] = []
            for node in nodes_to_use:
                subscriptions.extend(filter(self.can_execute, node.subscriptions))
                # print(subscriptions.extend(filter(self.can_execute, node.subscriptions)))
                # print(node.subscriptions)
                timers.extend(filter(self.can_execute, node.timers))
                # print(node.timers)
                clients.extend(filter(self.can_execute, node.clients))
                # print(node.clients)
                services.extend(filter(self.can_execute, node.services))
                node_guards = filter(self.can_execute, node.guards)
                waitables.extend(filter(self.can_execute, node.waitables))
                # retrigger a guard condition that was triggered but not handled
                for gc in node_guards:
                    if gc._executor_triggered:
                        gc.trigger()
                    guards.append(gc)

        

            if timeout_timer is not None:
                timers.append(timeout_timer)

            guards.append(self._guard)
            guards.append(self._sigint_gc)

            entity_count = NumberOfEntities(
                len(subscriptions), len(guards), len(timers), len(clients), len(services))
            for waitable in waitables:
                entity_count += waitable.get_num_entities()

            # Construct a wait set
            with _WaitSet() as wait_set, ExitStack() as context_stack:
                sub_capsules = []
                for sub in subscriptions:
                    try:
                        sub_capsules.append(context_stack.enter_context(sub.handle))
                    except InvalidHandle:
                        entity_count.num_subscriptions -= 1

                client_capsules = []
                for cli in clients:
                    try:
                        client_capsules.append(context_stack.enter_context(cli.handle))
                    except InvalidHandle:
                        entity_count.num_clients -= 1

                service_capsules = []
                for srv in services:
                    try:
                        service_capsules.append(context_stack.enter_context(srv.handle))
                    except InvalidHandle:
                        entity_count.num_services -= 1

                timer_capsules = []
                for tmr in timers:
                    try:
                        timer_capsules.append(context_stack.enter_context(tmr.handle))
                    except InvalidHandle:
                        entity_count.num_timers -= 1

                guard_capsules = []
                for gc in guards:
                    try:
                        guard_capsules.append(context_stack.enter_context(gc.handle))
                    except InvalidHandle:
                        entity_count.num_guard_conditions -= 1

                _rclpy.rclpy_wait_set_init(
                    wait_set,
                    entity_count.num_subscriptions,
                    entity_count.num_guard_conditions,
                    entity_count.num_timers,
                    entity_count.num_clients,
                    entity_count.num_services,
                    entity_count.num_events,
                    self._context.handle)

                _rclpy.rclpy_wait_set_clear_entities(wait_set)
                for sub_capsule in sub_capsules:
                    _rclpy.rclpy_wait_set_add_entity('subscription', wait_set, sub_capsule)
                for cli_capsule in client_capsules:
                    _rclpy.rclpy_wait_set_add_entity('client', wait_set, cli_capsule)
                for srv_capsule in service_capsules:
                    _rclpy.rclpy_wait_set_add_entity('service', wait_set, srv_capsule)
                for tmr_capsule in timer_capsules:
                    _rclpy.rclpy_wait_set_add_entity('timer', wait_set, tmr_capsule)
                for gc_capsule in guard_capsules:
                    _rclpy.rclpy_wait_set_add_entity('guard_condition', wait_set, gc_capsule)
                for waitable in waitables:
                    waitable.add_to_wait_set(wait_set)

                # Wait for something to become ready
                _rclpy.rclpy_wait(wait_set, timeout_nsec)
                if self._is_shutdown:handle.pointer
                    # raise ShutdownException()
                if not self._context.ok():
                    raise ExternalShutdownException()

                # get ready entities
                subs_ready = _rclpy.rclpy_get_ready_entities('subscription', wait_set)
                guards_ready = _rclpy.rclpy_get_ready_entities('guard_condition', wait_set)
                timers_ready = _rclpy.rclpy_get_ready_entities('timer', wait_set)
                clients_ready = _rclpy.rclpy_get_ready_entities('client', wait_set)
                services_ready = _rclpy.rclpy_get_ready_entities('service', wait_set)
         
                # Mark all guards as triggered before yielding since they're auto-taken
                for gc in guards:
                    if gc.handle.pointer in guards_ready:
                        gc._executor_triggered = True


                # Check waitables before wait set is destroyed
                for node in nodes_to_use:
                    for wt in node.waitables:
                        # Only check waitables that were added to the wait set
                        if wt in waitables and wt.is_ready(wait_set):
                            handler = self._make_handler(
                                wt, node, lambda e: e.take_data(), self._execute_waitable)
                            yielded_work = True
                            yield handler, wt, node
            for node in nodes_to_use:
                for tmr in node.timers:
                    if tmr.handle.pointer in timers_ready:
                        with tmr.handle as capsule:
                            # Check timer is ready to workaround rcl issue with cancelled timers
                            if _rclpy.rclpy_is_timer_ready(capsule):
                                if tmr.callback_group.can_execute(tmr):
                                    handler = self._make_handler(
                                        tmr, node, self._take_timer, self._execute_timer)
                                    yielded_work = True
                                    yield handler, tmr, node
            for node in nodes_to_use:
                if isinstance(node, Component):
                    for port in node.event_input_ports.values():
                        if port.subscription.handle.pointer in subs_ready:
                            if port.subscription.callback_group.can_execute(port.subscription):
                                handler = self._make_handler(port.subscription, node, self._take_subscription, self._execute_subscription)
                                yield_work = True
                                yield handler, port.subscription, node
            
            for node in nodes_to_use:
                if isinstance(node, Component):
                    for port in node.stream_input_ports.values():
                        if port.subscription.handle.pointer in subs_ready:
                            if port.subscription.callback_group.can_execute(port.subscription):
                                handler = self._make_handler(port.subscription, node, self._take_subscription, self._execute_subscription)
                                yield_work = True
                                yield handler, port.subscription, node
            
            for node in nodes_to_use:
                if not isinstance(node, Component):
                    for sub in node.subscriptions:
                        if sub.handle.pointer in subs_ready:
                            if sub.callback_group.can_execute(sub):
                                handler = self._make_handler(sub, node, self._take_subscription, self._execute_subscription)
                                yielded_work = True
                                yield handler, sub, node

            for node in nodes_to_use:
                for gc in node.guards:
                    if gc._executor_triggered:
                        if gc.callback_group.can_execute(gc):
                            handler = self._make_handler(
                                gc, node, self._take_guard_condition,
                                self._execute_guard_condition)
                            yielded_work = True
                            yield handler, gc, node
            for node in nodes_to_use:
                for client in node.clients:
                    if client.handle.pointer in clients_ready:
                        if client.callback_group.can_execute(client):
                            handler = self._make_handler(
                                client, node, self._take_client, self._execute_client)
                            yielded_work = True
                            yield handler, client, node
            for node in nodes_to_use:
                for srv in node.services:
                    if srv.handle.pointer in services_ready:
                        if srv.callback_group.can_execute(srv):
                            handler = self._make_handler(
                                srv, node, self._take_service, self._execute_service)
                            yielded_work = True
                            yield handler, srv, node

            # Check timeout timer
            if (
                timeout_nsec == 0 or
                (timeout_timer is not None and timeout_timer.handle.pointer in timers_ready)
            ):
                raise TimeoutException()
        if self._is_shutdown:
            raise ShutdownException()
        if condition():
            raise ConditionReachedException()

    

class _WaitSet:
    """Make sure the wait set gets destroyed when a generator exits."""

    def __enter__(self):
        self.wait_set = _rclpy.rclpy_get_zero_initialized_wait_set()
        return self.wait_set

    def __exit__(self, t, v, tb):
        _rclpy.rclpy_destroy_wait_set(self.wait_set)

class ConditionReachedException(Exception):
    """Future has been completed."""

    pass