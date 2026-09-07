#!/usr/bin/env python3
"""
Multithreaded Event Bus for Parallel Asset Generation

Provides a thread-safe event bus system for parallel processing of:
- Ollama prompt generation
- SD3.5 draft generation
- Image exports
- Audio generation
- Post-processing

Features:
- Priority-based routing: CRITICAL, HIGH, NORMAL, LOW queues
- Synchronous dispatch for CRITICAL events, async for others
- Multiple handlers per event type (all handlers called)
- Work stealing between worker threads (load balancing)
- Priority inheritance (boost dependent events when critical tasks depend on them)
- Deterministic result ordering (timestamp + job_id for reproducible merging)
- Thread-safe event publishing/subscribing
- Parallel task execution with worker pools
- Progress tracking and error handling
- Event result aggregation
- Automatic resource cleanup
- CPU thermal throttling with dynamic worker scaling
- Thread-to-core migration based on temperature and performance

Architecture:
- Separate priority queues (CRITICAL, HIGH, NORMAL, LOW)
- Event dispatcher/router pattern
- Work stealing for better load distribution
- Priority inheritance for dependency handling
- Deterministic result merging (maintains order)
- Multiple handler support (all handlers process each event)

Platform-Specific Implementations:
- Windows: Uses Windows API (SetThreadAffinityMask via ctypes) for CPU affinity
- Linux: Uses pthread_setaffinity_np (via ctypes) for CPU affinity
- Temperature Monitoring: Uses psutil (cross-platform), PowerShell WMI (Windows), 
  /sys/class/thermal (Linux) for per-core temperature readings
"""

from __future__ import annotations

import threading
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
from queue import Queue, Empty
from pathlib import Path
import traceback

# Try to import psutil for temperature monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Cache manager import is lazy (in __init__) to avoid circular imports
CACHE_AVAILABLE = True  # Will check at runtime

# Platform-specific imports for CPU affinity
try:
    import ctypes
    import ctypes.wintypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False

# Windows API constants and functions for thread affinity
if sys.platform == 'win32' and CTYPES_AVAILABLE:
    try:
        kernel32 = ctypes.windll.kernel32
        
        # Windows API constants
        THREAD_SET_INFORMATION = 0x0020
        ThreadAffinityMask = 0x0001
        
        # Function signatures
        SetThreadAffinityMask = kernel32.SetThreadAffinityMask
        SetThreadAffinityMask.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD_PTR]
        SetThreadAffinityMask.restype = ctypes.wintypes.DWORD_PTR
        
        GetCurrentThread = kernel32.GetCurrentThread
        GetCurrentThread.argtypes = []
        GetCurrentThread.restype = ctypes.wintypes.HANDLE
        
        WINDOWS_AFFINITY_AVAILABLE = True
    except Exception:
        WINDOWS_AFFINITY_AVAILABLE = False
else:
    WINDOWS_AFFINITY_AVAILABLE = False

# Linux-specific for CPU affinity
if sys.platform != 'win32' and CTYPES_AVAILABLE:
    try:
        import ctypes.util
        libc = None
        try:
            libc = ctypes.CDLL(ctypes.util.find_library('c'))
            if libc:
                # pthread_setaffinity_np signature
                libc.pthread_setaffinity_np.argtypes = [
                    ctypes.c_ulong,  # pthread_t
                    ctypes.c_size_t,  # cpusetsize
                    ctypes.POINTER(ctypes.c_ulong)  # cpuset
                ]
                libc.pthread_setaffinity_np.restype = ctypes.c_int
                LINUX_AFFINITY_AVAILABLE = True
            else:
                LINUX_AFFINITY_AVAILABLE = False
        except Exception:
            LINUX_AFFINITY_AVAILABLE = False
    except Exception:
        LINUX_AFFINITY_AVAILABLE = False
else:
    LINUX_AFFINITY_AVAILABLE = False


class EventType(Enum):
    """Types of events in the asset generation pipeline."""
    PROMPT_GENERATION = "prompt_generation"
    SD35_DRAFT = "sd35_draft"
    IMAGE_EXPORT = "image_export"
    IMAGE_POSTPROCESS = "image_postprocess"
    AUDIO_GENERATION = "audio_generation"
    PREVIEW_COMPOSITION = "preview_composition"
    JOB_SPEC_SAVE = "job_spec_save"
    ART_DIRECTOR_REVIEW = "art_director_review"  # Art director critiques generated assets
    SD35_REFINE = "sd35_refine"  # Refinement pass based on art director feedback
    # Thermal management events (event-driven architecture)
    THREAD_HEAT = "thread_heat"  # Thread health monitor publishes this
    WORK_REBALANCE = "work_rebalance"  # Load balancer publishes this to migrate tasks
    SYSTEM_THROTTLE = "system_throttle"  # System-wide thermal backpressure
    TASK_ACCEPTED = "task_accepted"  # Worker acknowledges task receipt


class Priority(Enum):
    """Event priority levels (CDDA-inspired)."""
    CRITICAL = 100  # Synchronous dispatch, highest priority
    HIGH = 50       # Async, high priority
    NORMAL = 0      # Async, normal priority
    LOW = -50       # Async, low priority


@dataclass
class Event:
    """Represents an event in the bus."""
    event_type: EventType
    job_id: str
    payload: Dict[str, Any]
    priority: int = 0  # Higher priority = processed first (or use Priority enum)
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    sync_dispatch: bool = False  # If True, dispatch synchronously (CRITICAL)
    dependencies: List[str] = field(default_factory=list)  # Event IDs this depends on
    boosted_priority: Optional[int] = None  # Temporary priority boost (priority inheritance)


@dataclass
class EventResult:
    """Result of processing an event."""
    event_type: EventType
    job_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """
    Multithreaded event bus for parallel asset generation.
    
    Thread-safe event publishing and processing with worker pools.
    Includes CPU temperature monitoring and dynamic worker scaling.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        verbose: bool = False,
        max_temp_c: float = 75.0,
        temp_check_interval: float = 2.0,
        enable_thermal_throttling: bool = True
    ):
        """
        Initialize event bus.
        
        Args:
            max_workers: Maximum number of worker threads (None = auto-detect)
            verbose: Print detailed progress
            max_temp_c: Maximum CPU temperature in Celsius before throttling (default: 75°C)
            temp_check_interval: Seconds between temperature checks (default: 2.0)
            enable_thermal_throttling: Enable temperature-based worker scaling (default: True)
        """
        import multiprocessing
        self._base_max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        self.max_workers = self._base_max_workers
        self.verbose = verbose
        self.max_temp_c = max_temp_c
        self.temp_check_interval = temp_check_interval
        self.enable_thermal_throttling = enable_thermal_throttling and PSUTIL_AVAILABLE
        
        # Thermal throttling state
        self._current_temp: Optional[float] = None
        self._per_core_temps: Dict[int, float] = {}  # Core ID -> temperature
        self._temp_monitor_thread: Optional[threading.Thread] = None
        self._temp_monitor_running = False
        self._max_concurrent_work = self.max_workers  # Dynamically adjusted based on temperature
        self._active_work_count = 0  # Current number of workers processing events
        self._throttle_lock = threading.Lock()
        
        # Thread-to-core affinity management
        self._thread_affinities: Dict[threading.Thread, int] = {}  # Thread -> core ID
        self._core_performance: Dict[int, float] = {}  # Core ID -> performance score (higher = faster)
        self._core_usage: Dict[int, int] = {}  # Core ID -> number of threads using it
        self._affinity_lock = threading.Lock()
        self._enable_thread_migration = enable_thermal_throttling and PSUTIL_AVAILABLE
        self._temp_spike_threshold = 5.0  # °C increase to trigger migration
        self._last_migration_time = 0.0
        self._migration_cooldown = 10.0  # Seconds between migrations
        
        # Temperature thresholds (Celsius)
        self._temp_critical = max_temp_c  # 75°C - reduce workers significantly
        self._temp_warning = max_temp_c - 5.0  # 70°C - start reducing workers
        self._temp_safe = max_temp_c - 15.0  # 60°C - can increase workers
        self._temp_optimal = max_temp_c - 25.0  # 50°C - full worker count
        
        # Priority queues (separate queues per priority level)
        self._priority_queues: Dict[int, Queue] = {
            Priority.CRITICAL.value: Queue(),
            Priority.HIGH.value: Queue(),
            Priority.NORMAL.value: Queue(),
            Priority.LOW.value: Queue(),
        }
        self._queue_locks: Dict[int, threading.Lock] = {
            priority: threading.Lock() for priority in self._priority_queues.keys()
        }
        
        # Results with deterministic ordering (by timestamp + job_id)
        self._results: Dict[str, EventResult] = {}
        self._results_lock = threading.Lock()
        self._result_order: List[str] = []  # Maintain order for deterministic merging
        
        # Event handlers: event_type -> list of handlers (support multiple handlers)
        self._handlers: Dict[EventType, List[Callable[[Event], EventResult]]] = {}
        self._handlers_lock = threading.Lock()
        
        # Work stealing: per-worker local queues
        self._worker_local_queues: Dict[threading.Thread, Queue] = {}
        self._worker_queue_lock = threading.Lock()
        
        # Priority inheritance tracking
        self._priority_boosts: Dict[str, int] = {}  # job_id -> boosted priority
        
        # Worker pool
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running = False
        self._stop_event = threading.Event()
        
        # Statistics
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "events_retried": 0,
            "total_duration": 0.0,
            "thermal_throttles": 0,
            "thermal_resumes": 0,
            "thread_migrations": 0,
        }
        self._stats_lock = threading.Lock()
        
        # Initialize core performance scores (estimate based on CPU frequency if available)
        if self._enable_thread_migration:
            self._initialize_core_performance()
        
        # Initialize temperature cache (simple in-memory cache)
        # Lazy import to avoid circular dependencies
        self._temp_cache = None
        try:
            from cache_manager import CacheManager
            self._temp_cache = CacheManager(max_size=100, default_ttl=1.0, enable_disk_cache=False, verbose=False)
        except ImportError:
            pass  # Cache not available
        
        if self.verbose and not PSUTIL_AVAILABLE:
            print(f"  [WARN] psutil not available; thermal throttling disabled")
        elif self.verbose and self.enable_thermal_throttling:
            print(f"  [INFO] Thermal throttling enabled (max: {max_temp_c}°C)")
        
        # Event-driven thermal management components
        self._health_monitor: Optional[ThreadHealthMonitor] = None
        self._load_balancer: Optional[ThermalAwareLoadBalancer] = None
        
        if self.enable_thermal_throttling and PSUTIL_AVAILABLE:
            # Initialize health monitor
            self._health_monitor = ThreadHealthMonitor(
                event_bus=self,
                check_interval=0.1,  # 100ms
                verbose=verbose
            )
            
            # Initialize load balancer
            self._load_balancer = ThermalAwareLoadBalancer(
                event_bus=self,
                health_monitor=self._health_monitor,
                verbose=verbose
            )
            
            # Subscribe to WorkRebalanceEvent to handle task migration
            self.subscribe(EventType.WORK_REBALANCE, self._handle_work_rebalance)
            
            # Subscribe to SystemThrottleEvent for backpressure
            self.subscribe(EventType.SYSTEM_THROTTLE, self._handle_system_throttle)
            
            if self.verbose:
                print(f"  [INFO] Event-driven thermal management initialized")
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], EventResult]
    ) -> None:
        """
        Subscribe a handler function to an event type.
        
        Args:
            event_type: Type of event to handle
            handler: Function that takes Event and returns EventResult
        """
        with self._handlers_lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
    
    def publish(
        self,
        event_type: EventType,
        job_id: str,
        payload: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
        sync_dispatch: Optional[bool] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Publish an event to the bus with priority-based routing.
        
        Args:
            event_type: Type of event
            job_id: Unique identifier for this job/asset
            payload: Event data
            priority: Priority level (use Priority enum values or int)
            max_retries: Maximum retry attempts on failure
            sync_dispatch: Force synchronous dispatch (None = auto-detect from priority)
            dependencies: List of event IDs this event depends on
        
        Returns:
            Event ID (for tracking)
        """
        # Auto-detect sync dispatch for CRITICAL priority
        if sync_dispatch is None:
            sync_dispatch = (priority >= Priority.CRITICAL.value)
        
        event = Event(
            event_type=event_type,
            job_id=job_id,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            sync_dispatch=sync_dispatch,
            dependencies=dependencies or []
        )
        
        # Route to appropriate priority queue
        priority_level = self._get_priority_level(priority)
        target_queue = self._priority_queues.get(priority_level, self._priority_queues[Priority.NORMAL.value])
        
        # Add to priority queue with timestamp for deterministic ordering
        target_queue.put((priority, time.time(), job_id, event))
        
        # If sync dispatch, process immediately
        if sync_dispatch:
            if self.verbose:
                print(f"  [EVENT] Published (SYNC): {event_type.value} for {job_id}")
            # Process synchronously in current thread
            result = self._process_event(event)
            result_key = f"{event_type.value}:{job_id}"
            with self._results_lock:
                self._results[result_key] = result
                if result_key not in self._result_order:
                    self._result_order.append(result_key)
            return f"{event_type.value}:{job_id}"
        
        if self.verbose:
            print(f"  [EVENT] Published: {event_type.value} for {job_id} (priority: {priority})")
        
        return f"{event_type.value}:{job_id}"
    
    def _get_priority_level(self, priority: int) -> int:
        """Map priority value to priority level queue."""
        if priority >= Priority.CRITICAL.value:
            return Priority.CRITICAL.value
        elif priority >= Priority.HIGH.value:
            return Priority.HIGH.value
        elif priority >= Priority.LOW.value:
            return Priority.NORMAL.value
        else:
            return Priority.LOW.value
    
    def _process_event(self, event: Event) -> EventResult:
        """
        Process a single event using all registered handlers (multiple handlers supported).
        
        Args:
            event: Event to process
        
        Returns:
            EventResult (aggregated from all handlers)
        """
        start_time = time.time()
        
        # Check dependencies first (priority inheritance)
        if event.dependencies:
            self._boost_dependent_priorities(event)
        
        with self._handlers_lock:
            handlers = self._handlers.get(event.event_type, [])
        
        if not handlers:
            return EventResult(
                event_type=event.event_type,
                job_id=event.job_id,
                success=False,
                error=f"No handler registered for {event.event_type.value}",
                duration=time.time() - start_time
            )
        
        # Process all handlers (multiple handlers per event)
        results = []
        for handler in handlers:
            try:
                handler_result = handler(event)
                results.append(handler_result)
            except Exception as e:
                error_msg = f"Handler exception: {str(e)}"
                if self.verbose:
                    print(f"    [ERROR] {error_msg}")
                    traceback.print_exc()
                results.append(EventResult(
                    event_type=event.event_type,
                    job_id=event.job_id,
                    success=False,
                    error=error_msg,
                    duration=0.0
                ))
        
        # Aggregate results (success if any handler succeeds)
        aggregated = EventResult(
            event_type=event.event_type,
            job_id=event.job_id,
            success=any(r.success for r in results),
            result=[r.result for r in results if r.result is not None],
            error="; ".join([r.error for r in results if r.error]),
            duration=time.time() - start_time
        )
        
        # Restore priority boosts
        if event.dependencies:
            self._restore_dependent_priorities(event)
        
        return aggregated
    
    def _boost_dependent_priorities(self, event: Event) -> None:
        """Boost priority of dependent events (priority inheritance)."""
        if not event.dependencies:
            return
        
        # Boost priority of dependencies that haven't completed yet
        for dep_id in event.dependencies:
            # Parse dependency ID (format: "event_type:job_id")
            if ':' not in dep_id:
                continue
            
            dep_type_str, dep_job_id = dep_id.split(':', 1)
            
            # Check if dependency is already complete
            with self._results_lock:
                if dep_id in [f"{et.value}:{dep_job_id}" for et in EventType]:
                    # Check if result exists
                    result_exists = False
                    for et in EventType:
                        test_key = f"{et.value}:{dep_job_id}"
                        if test_key in self._results:
                            result_exists = True
                            break
                    
                    if result_exists:
                        continue  # Dependency already completed
            
            # Dependency not yet processed, boost it
            if dep_job_id not in self._priority_boosts:
                # Boost to at least the current event's priority
                self._priority_boosts[dep_job_id] = max(event.priority, self._priority_boosts.get(dep_job_id, 0))
                if self.verbose:
                    print(f"    [PRIORITY] Boosted dependency {dep_job_id} to {self._priority_boosts[dep_job_id]}")
    
    def _restore_dependent_priorities(self, event: Event) -> None:
        """Restore original priorities of dependent events."""
        for dep_id in event.dependencies:
            if ':' in dep_id:
                _, dep_job_id = dep_id.split(':', 1)
                if dep_job_id in self._priority_boosts:
                    del self._priority_boosts[dep_job_id]
    
    def _worker_loop(self) -> None:
        """Worker thread loop with work stealing for load balancing."""
        current_thread = threading.current_thread()
        initial_core_assigned = False
        
        # Initialize local queue for this worker (work stealing)
        with self._worker_queue_lock:
            self._worker_local_queues[current_thread] = Queue()
        local_queue = self._worker_local_queues[current_thread]
        
        while not self._stop_event.is_set():
            try:
                # Assign initial core affinity (prioritize faster cores)
                if self._enable_thread_migration and not initial_core_assigned:
                    # Find the best available core (fastest, coolest, least used)
                    best_core = None
                    best_score = -1
                    
                    with self._affinity_lock:
                        # Wait for core performance to be initialized
                        if not self._core_performance:
                            time.sleep(0.1)
                            continue
                        
                        for core_id in self._core_performance.keys():
                            temp = self._per_core_temps.get(core_id, 50.0)  # Default to 50°C if unknown
                            perf = self._core_performance.get(core_id, 1.0)
                            usage = self._core_usage.get(core_id, 0)
                            
                            # Score = performance / (temperature * (usage + 1))
                            # Higher score = better (prioritizes faster, cooler, less-used cores)
                            score = perf / (max(temp, 1.0) * (usage + 1))
                            
                            if score > best_score:
                                best_score = score
                                best_core = core_id
                        
                        if best_core is not None:
                            self._set_thread_affinity(current_thread, best_core)
                            initial_core_assigned = True
                            if self.verbose:
                                perf = self._core_performance.get(best_core, 0)
                                temp = self._per_core_temps.get(best_core, 0)
                                print(f"    [AFFINITY] Thread {current_thread.name} assigned to core {best_core} "
                                      f"(perf: {perf:.0f}MHz, temp: {temp:.1f}°C)")
                
                # Try to get event (work stealing pattern: local queue first, then priority queues, then steal)
                event = None
                priority = 0
                timestamp = 0.0
                job_id = ""
                
                # 1. Try local queue first
                try:
                    priority, timestamp, job_id, event = local_queue.get_nowait()
                except Empty:
                    # 2. Try priority queues (CRITICAL -> HIGH -> NORMAL -> LOW)
                    for prio_level in [Priority.CRITICAL.value, Priority.HIGH.value, Priority.NORMAL.value, Priority.LOW.value]:
                        queue = self._priority_queues[prio_level]
                        try:
                            priority, timestamp, job_id, event = queue.get_nowait()
                            break
                        except Empty:
                            continue
                    
                    # 3. Work stealing: try to steal from other workers
                    if event is None:
                        event = self._steal_work(current_thread)
                        if event:
                            priority = event.priority
                            timestamp = event.timestamp
                            job_id = event.job_id
                
                # 4. If still no event, wait on priority queues with timeout (try all in priority order)
                if event is None:
                    got_event = False
                    for prio_level in [Priority.CRITICAL.value, Priority.HIGH.value, Priority.NORMAL.value, Priority.LOW.value]:
                        queue = self._priority_queues[prio_level]
                        try:
                            priority, timestamp, job_id, event = queue.get(timeout=0.1)
                            got_event = True
                            break
                        except Empty:
                            continue
                    
                    if not got_event:
                        continue
                
                # Apply priority boost if applicable
                if job_id in self._priority_boosts:
                    event.boosted_priority = self._priority_boosts[job_id]
                    effective_priority = max(priority, event.boosted_priority)
                    if self.verbose and effective_priority > priority:
                        print(f"    [PRIORITY] Event {job_id} boosted from {priority} to {effective_priority}")
                    priority = effective_priority
                
                # Acquire work permit (blocks if too many workers active due to thermal throttling)
                if self.enable_thermal_throttling:
                    # Check if this thread is in cooling pool - if so, yield to active pool threads
                    if self._load_balancer:
                        thread_id = f"thread_{current_thread.ident}"
                        if self._load_balancer.is_thread_throttled(thread_id):
                            # Thread is in cooling pool - yield work to active pool
                            if not self._load_balancer.is_thread_in_active_pool(thread_id):
                                # Brief pause to let active pool threads process
                                time.sleep(0.1)
                                continue  # Skip this iteration, let active pool threads work
                    
                    # Check if this thread is on a hot core and migrate to a cooler one
                    if self._enable_thread_migration:
                        with self._affinity_lock:
                            thread_core = self._thread_affinities.get(current_thread)
                            if thread_core is not None:
                                core_temp = self._per_core_temps.get(thread_core)
                                if core_temp is not None and core_temp >= self._temp_warning:
                                    # Thread is on a hot core - migrate to a cooler core
                                    cooler_core = self._find_cooler_core(thread_core)
                                    if cooler_core is not None:
                                        # Migrate to cooler core
                                        if self._set_thread_affinity(current_thread, cooler_core):
                                            if self.verbose:
                                                old_temp = core_temp
                                                new_temp = self._per_core_temps.get(cooler_core, 0)
                                                print(f"    [MIGRATE] Thread {current_thread.name} migrated from core {thread_core} "
                                                      f"({old_temp:.1f}°C) to core {cooler_core} ({new_temp:.1f}°C)")
                                            # Update core usage tracking
                                            if thread_core in self._core_usage:
                                                self._core_usage[thread_core] = max(0, self._core_usage[thread_core] - 1)
                                            self._core_usage[cooler_core] = self._core_usage.get(cooler_core, 0) + 1
                                            with self._stats_lock:
                                                self._stats["thread_migrations"] = self._stats.get("thread_migrations", 0) + 1
                                    elif core_temp >= self._temp_critical:
                                        # No cooler core available and critical temp - brief pause to let core cool
                                        time.sleep(0.2)  # Short pause only when migration not possible
                    
                    # Check current temperature and max concurrent work limit
                    with self._throttle_lock:
                        max_concurrent = self._max_concurrent_work
                        current_count = self._active_work_count
                        temp = self._current_temp
                    
                    # Wait if we're at the limit
                    while current_count >= max_concurrent and not self._stop_event.is_set():
                        # Add delay based on temperature severity
                        if temp is not None and temp >= self._temp_critical:
                            time.sleep(2.0)  # Longer pause when critical
                        elif temp is not None and temp >= self._temp_warning:
                            time.sleep(1.0)  # Medium pause when warning
                        else:
                            time.sleep(0.5)  # Short pause otherwise
                        
                        # Re-check limits
                        with self._throttle_lock:
                            max_concurrent = self._max_concurrent_work
                            current_count = self._active_work_count
                            temp = self._current_temp
                    
                    if self._stop_event.is_set():
                        # Put event back to appropriate priority queue and exit
                        priority_level = self._get_priority_level(priority)
                        target_queue = self._priority_queues.get(priority_level, self._priority_queues[Priority.NORMAL.value])
                        target_queue.put((priority, time.time(), job_id, event))
                        continue
                    
                    # Increment active work count
                    with self._throttle_lock:
                        self._active_work_count += 1
                
                try:
                    if self.verbose:
                        print(f"    [WORKER] Processing: {event.event_type.value} for {event.job_id}")
                    
                    # Record task start for health monitoring
                    if self._health_monitor:
                        thread_id = f"thread_{current_thread.ident}"
                        self._health_monitor.record_task_start(thread_id)
                    
                    # Process event
                    result = self._process_event(event)
                    
                    # Record task end for health monitoring
                    if self._health_monitor:
                        thread_id = f"thread_{current_thread.ident}"
                        self._health_monitor.record_task_end(thread_id)
                finally:
                    # Decrement active work count
                    if self.enable_thermal_throttling:
                        with self._throttle_lock:
                            self._active_work_count = max(0, self._active_work_count - 1)
                
                    # Store result with deterministic ordering
                    result_key = f"{event.event_type.value}:{event.job_id}"
                    with self._results_lock:
                        self._results[result_key] = result
                        # Maintain order for deterministic merging (by timestamp + job_id)
                        if result_key not in self._result_order:
                            # Insert in sorted order
                            insert_pos = len(self._result_order)
                            for i, existing_key in enumerate(self._result_order):
                                existing_result = self._results.get(existing_key)
                                if existing_result and existing_result.timestamp > result.timestamp:
                                    insert_pos = i
                                elif existing_result and existing_result.timestamp == result.timestamp:
                                    # Tie-break by job_id
                                    if existing_key > result_key:
                                        insert_pos = i
                                if insert_pos < len(self._result_order):
                                    break
                            self._result_order.insert(insert_pos, result_key)
                    
                    # Update statistics
                    with self._stats_lock:
                        self._stats["events_processed"] += 1
                        self._stats["total_duration"] += result.duration
                        if not result.success:
                            self._stats["events_failed"] += 1
                    
                    # Retry logic if failed
                    if not result.success and event.retry_count < event.max_retries:
                        event.retry_count += 1
                        with self._stats_lock:
                            self._stats["events_retried"] += 1
                        if self.verbose:
                            print(f"    [RETRY] Retrying {event.event_type.value} for {event.job_id} (attempt {event.retry_count + 1}/{event.max_retries + 1})")
                        # Re-queue with same priority (or boosted priority if applicable)
                        retry_priority = event.boosted_priority if event.boosted_priority else event.priority
                        priority_level = self._get_priority_level(retry_priority)
                        target_queue = self._priority_queues.get(priority_level, self._priority_queues[Priority.NORMAL.value])
                        target_queue.put((retry_priority, time.time(), event.job_id, event))
                        # Don't mark task done yet - it will be done after retry succeeds
                    else:
                        # Mark task done (use appropriate queue)
                        priority_level = self._get_priority_level(priority)
                        target_queue = self._priority_queues.get(priority_level, self._priority_queues[Priority.NORMAL.value])
                        target_queue.task_done()
                
            except Exception as e:
                if self.verbose:
                    print(f"    [ERROR] Worker exception: {e}")
                    traceback.print_exc()
                # Make sure to release semaphore on error
                if self.enable_thermal_throttling:
                    try:
                        self._work_semaphore.release()
                    except:
                        pass
    
    def _steal_work(self, thief_thread: threading.Thread) -> Optional[Event]:
        """
        Work stealing: try to steal work from other workers for load balancing.
        
        Args:
            thief_thread: Thread attempting to steal work
        
        Returns:
            Event if work was stolen, None otherwise
        """
        with self._worker_queue_lock:
            workers = list(self._worker_local_queues.keys())
        
        # Try to steal from other workers (random order to avoid contention)
        import random
        random.shuffle(workers)
        
        for worker_thread in workers:
            if worker_thread == thief_thread:
                continue
            
            if not worker_thread.is_alive():
                continue
            
            local_queue = self._worker_local_queues.get(worker_thread)
            if local_queue is None:
                continue
            
            # Try to steal from their local queue
            try:
                priority, timestamp, job_id, event = local_queue.get_nowait()
                if self.verbose:
                    print(f"    [STEAL] Worker {thief_thread.name} stole work from {worker_thread.name} ({event.event_type.value})")
                return event
            except Empty:
                continue
            except Exception as e:
                if self.verbose:
                    print(f"    [WARN] Work stealing error: {e}")
                continue
        
        return None
    
    def _initialize_core_performance(self) -> None:
        """Initialize core performance scores based on CPU frequency."""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            # Get CPU frequency per core (if available)
            cpu_freq = psutil.cpu_freq(per_cpu=True)
            if cpu_freq:
                for core_id, freq_info in enumerate(cpu_freq):
                    if freq_info:
                        # Use max frequency as performance indicator
                        perf_score = freq_info.max if freq_info.max > 0 else freq_info.current
                        self._core_performance[core_id] = perf_score
                    else:
                        # Default performance score
                        self._core_performance[core_id] = 1.0
            else:
                # Fallback: assume all cores have equal performance
                import multiprocessing
                num_cores = multiprocessing.cpu_count()
                for core_id in range(num_cores):
                    self._core_performance[core_id] = 1.0
            
            # Initialize core usage tracking
            for core_id in self._core_performance.keys():
                self._core_usage[core_id] = 0
            
            if self.verbose:
                print(f"  [INFO] Initialized {len(self._core_performance)} core performance scores")
        except Exception as e:
            if self.verbose:
                print(f"  [WARN] Could not initialize core performance: {e}")
    
    def _get_cpu_temperature(self, use_cache: bool = True) -> Optional[float]:
        """
        Get current CPU temperature in Celsius, with caching.
        
        Args:
            use_cache: Use cached temperature (1 second TTL)
        
        Returns:
            Temperature in Celsius, or None if unavailable
        """
        if not PSUTIL_AVAILABLE:
            return None
        
        # Check cache first (1 second TTL to avoid excessive sensor reads)
        if use_cache and hasattr(self, '_temp_cache'):
            cached = self._temp_cache.get("cpu_temp", ttl=1.0, use_disk=False)
            if cached is not None:
                return cached
        
        try:
            # Try to get CPU temperature
            # psutil.sensors_temperatures() returns a dict of sensor groups
            temps = psutil.sensors_temperatures()
            
            # Look for CPU temperature in common sensor names
            cpu_temp = None
            for sensor_group, sensors in temps.items():
                for sensor in sensors:
                    label_lower = sensor.label.lower()
                    if 'cpu' in label_lower or 'core' in label_lower or 'package' in label_lower:
                        if cpu_temp is None or sensor.current > cpu_temp:
                            cpu_temp = sensor.current
            
            # If no CPU-specific sensor found, use the highest temperature
            if cpu_temp is None:
                for sensor_group, sensors in temps.items():
                    for sensor in sensors:
                        if cpu_temp is None or sensor.current > cpu_temp:
                            cpu_temp = sensor.current
            
            # Cache result
            if use_cache and hasattr(self, '_temp_cache'):
                self._temp_cache.set("cpu_temp", value=cpu_temp, ttl=1.0, use_disk=False)
            
            return cpu_temp
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] Could not read CPU temperature: {e}")
            return None
    
    def _get_per_core_temperatures(self) -> Dict[int, float]:
        """
        Get per-core CPU temperatures using platform-specific methods.
        
        Uses psutil on all platforms, with Windows WMI fallback if available.
        
        Returns:
            Dict mapping core ID to temperature in Celsius
        """
        if not PSUTIL_AVAILABLE:
            return {}
        
        per_core = {}
        
        try:
            # Method 1: Try psutil sensors (works on Linux, macOS, some Windows)
            temps = psutil.sensors_temperatures()
            
            # Try to extract per-core temperatures
            for sensor_group, sensors in temps.items():
                for sensor in sensors:
                    label_lower = sensor.label.lower()
                    # Look for core-specific sensors (e.g., "Core 0", "CPU Core #0")
                    if 'core' in label_lower:
                        # Try to extract core number from label
                        import re
                        match = re.search(r'(\d+)', sensor.label)
                        if match:
                            core_id = int(match.group(1))
                            per_core[core_id] = sensor.current
                    elif 'cpu' in label_lower and 'package' not in label_lower:
                        # Might be per-core, try to extract number
                        import re
                        match = re.search(r'(\d+)', sensor.label)
                        if match:
                            core_id = int(match.group(1))
                            per_core[core_id] = sensor.current
            
            # Method 2: Windows PowerShell script fallback (if psutil didn't find per-core temps)
            if sys.platform == 'win32' and not per_core:
                try:
                    import subprocess
                    # Try PowerShell script first (more reliable)
                    script_path = Path(__file__).parent / "get_cpu_temps.ps1"
                    if script_path.exists():
                        result = subprocess.run(
                            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(script_path)],
                            capture_output=True,
                            text=True,
                            timeout=3
                        )
                        if result.returncode == 0:
                            # Parse output (format: "0:45.2\n1:46.1\n...")
                            for line in result.stdout.strip().split('\n'):
                                if ':' in line:
                                    try:
                                        core_id, temp_str = line.split(':', 1)
                                        per_core[int(core_id)] = float(temp_str)
                                    except ValueError:
                                        continue
                    else:
                        # Fallback: Use wmic directly
                        result = subprocess.run(
                            ['wmic', '/namespace:\\\\root\\wmi', 'path', 'MSAcpi_ThermalZoneTemperature', 'get', 'CurrentTemperature'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if result.returncode == 0:
                            # Parse WMI output (temperature is in 10th of Kelvin)
                            lines = result.stdout.strip().split('\n')
                            for i, line in enumerate(lines[1:], 0):  # Skip header
                                try:
                                    temp_kelvin_10th = int(line.strip())
                                    temp_celsius = (temp_kelvin_10th / 10.0) - 273.15
                                    per_core[i] = temp_celsius
                                except ValueError:
                                    continue
                except Exception as e:
                    if self.verbose:
                        print(f"    [WARN] Windows temperature fallback failed: {e}")
                    pass  # Fallback failed
            
            # Method 3: Linux /sys/class/thermal fallback
            if sys.platform != 'win32' and not per_core:
                try:
                    import os
                    import glob
                    # Try to read from /sys/class/thermal
                    thermal_zones = glob.glob('/sys/class/thermal/thermal_zone*/temp')
                    for i, zone_path in enumerate(thermal_zones):
                        try:
                            with open(zone_path, 'r') as f:
                                temp_millidegrees = int(f.read().strip())
                                temp_celsius = temp_millidegrees / 1000.0
                                # Try to get zone type to identify CPU cores
                                zone_type_path = zone_path.replace('/temp', '/type')
                                if os.path.exists(zone_type_path):
                                    with open(zone_type_path, 'r') as tf:
                                        zone_type = tf.read().strip().lower()
                                        if 'cpu' in zone_type or 'core' in zone_type:
                                            # Extract core number if possible
                                            import re
                                            match = re.search(r'(\d+)', zone_type)
                                            if match:
                                                core_id = int(match.group(1))
                                                per_core[core_id] = temp_celsius
                                            else:
                                                per_core[i] = temp_celsius
                        except (IOError, ValueError):
                            continue
                except Exception:
                    pass  # /sys fallback failed
            
            # Fallback: If we couldn't get per-core temps, distribute average temp
            if not per_core and self._current_temp is not None:
                import multiprocessing
                num_cores = multiprocessing.cpu_count()
                avg_temp = self._current_temp
                # Add some variation based on core usage (more used = slightly hotter)
                for core_id in range(num_cores):
                    usage_factor = self._core_usage.get(core_id, 0) * 0.5  # 0.5°C per thread
                    per_core[core_id] = avg_temp + usage_factor
            
            return per_core
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] Could not read per-core temperatures: {e}")
            return {}
    
    def _set_thread_affinity(self, thread: threading.Thread, core_id: int) -> bool:
        """
        Set CPU affinity for a thread to a specific core using platform-specific APIs.
        
        Uses Windows API on Windows, pthread on Linux, or falls back to tracking.
        
        Args:
            thread: Thread to set affinity for
            core_id: Core ID to bind thread to
        
        Returns:
            True if successful, False otherwise
        """
        if not PSUTIL_AVAILABLE:
            return False
        
        try:
            # Update tracking
            with self._affinity_lock:
                old_core = self._thread_affinities.get(thread)
                if old_core is not None and old_core in self._core_usage:
                    self._core_usage[old_core] = max(0, self._core_usage[old_core] - 1)
                
                self._thread_affinities[thread] = core_id
                # Update core usage
                if core_id in self._core_usage:
                    self._core_usage[core_id] += 1
            
            # Windows: Use SetThreadAffinityMask API
            if sys.platform == 'win32' and WINDOWS_AFFINITY_AVAILABLE:
                try:
                    # Only set affinity if this is the current thread
                    if thread == threading.current_thread():
                        thread_handle = GetCurrentThread()
                        # Create affinity mask (1 bit set for target core)
                        affinity_mask = 1 << core_id
                        result = SetThreadAffinityMask(thread_handle, affinity_mask)
                        if result != 0:
                            return True
                except Exception as e:
                    if self.verbose:
                        print(f"    [WARN] Windows affinity API failed: {e}")
            
            # Linux: Use pthread_setaffinity_np
            elif sys.platform != 'win32' and LINUX_AFFINITY_AVAILABLE:
                try:
                    # Only set affinity if this is the current thread
                    if thread == threading.current_thread():
                        thread_id = thread.ident
                        if thread_id and libc:
                            # Create CPU set (bitmask)
                            cpu_set = (ctypes.c_ulong * 1)()
                            cpu_set[0] = 1 << core_id
                            result = libc.pthread_setaffinity_np(
                                ctypes.c_ulong(thread_id),
                                ctypes.sizeof(cpu_set),
                                ctypes.cast(cpu_set, ctypes.POINTER(ctypes.c_ulong))
                            )
                            if result == 0:
                                return True
                except Exception as e:
                    if self.verbose:
                        print(f"    [WARN] Linux affinity API failed: {e}")
            
            # Fallback: Use process-level affinity (less precise but works)
            try:
                current_process = psutil.Process()
                current_affinity = current_process.cpu_affinity()
                
                # If target core is not in affinity, add it
                # This gives the OS scheduler a hint
                if core_id not in current_affinity:
                    # Try to set affinity to include target core
                    # But keep existing cores to avoid disrupting other threads
                    new_affinity = list(set(current_affinity + [core_id]))
                    if len(new_affinity) <= len(current_affinity) + 2:  # Limit expansion
                        current_process.cpu_affinity(new_affinity)
            except Exception:
                pass  # Fallback failed, but tracking is still updated
            
            return True  # Tracking updated even if API call failed
        except Exception as e:
            if self.verbose:
                print(f"    [WARN] Could not set thread affinity: {e}")
            return False
    
    def _find_cooler_core(self, current_core: int, exclude_cores: Optional[List[int]] = None) -> Optional[int]:
        """
        Find a cooler core to migrate to, prioritizing faster cores.
        
        Args:
            current_core: Current core ID
            exclude_cores: List of core IDs to exclude
        
        Returns:
            Cooler core ID, or None if none found
        """
        if not self._per_core_temps or current_core not in self._per_core_temps:
            return None
        
        current_temp = self._per_core_temps.get(current_core, float('inf'))
        exclude_cores = exclude_cores or []
        
        # Find cores that are cooler and available
        candidates = []
        for core_id, temp in self._per_core_temps.items():
            if core_id == current_core or core_id in exclude_cores:
                continue
            
            # Must be at least 3°C cooler to consider migration
            if temp < (current_temp - 3.0):
                # Calculate score: prioritize cooler AND faster cores
                temp_diff = current_temp - temp  # Positive = cooler
                perf_score = self._core_performance.get(core_id, 1.0)
                usage = self._core_usage.get(core_id, 0)
                
                # Score = (temp difference * performance) / (usage + 1)
                # Higher score = better candidate
                score = (temp_diff * perf_score) / (usage + 1)
                candidates.append((core_id, score, temp, perf_score))
        
        if not candidates:
            return None
        
        # Sort by score (highest first) - prioritizes faster, cooler, less-used cores
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best candidate
        return candidates[0][0]
    
    def _migrate_threads_from_hot_cores(self) -> int:
        """
        Migrate threads from hot cores to cooler cores when temperature spikes.
        
        Returns:
            Number of threads migrated
        """
        if not self._enable_thread_migration:
            return 0
        
        # Check cooldown
        current_time = time.time()
        if current_time - self._last_migration_time < self._migration_cooldown:
            return 0
        
        migrated = 0
        
        with self._affinity_lock:
            # Find hot cores (above warning threshold)
            hot_cores = [
                core_id for core_id, temp in self._per_core_temps.items()
                if temp >= self._temp_warning
            ]
            
            if not hot_cores:
                return 0
            
            # Get threads on hot cores
            threads_to_migrate = []
            for thread, core_id in self._thread_affinities.items():
                if core_id in hot_cores and thread.is_alive():
                    threads_to_migrate.append((thread, core_id))
            
            if not threads_to_migrate:
                return 0
            
            # Sort by temperature (hottest first) and performance (faster first)
            threads_to_migrate.sort(
                key=lambda x: (
                    self._per_core_temps.get(x[1], 0),
                    -self._core_performance.get(x[1], 0)  # Negative for descending
                ),
                reverse=True
            )
            
            # Migrate threads
            for thread, old_core in threads_to_migrate:
                new_core = self._find_cooler_core(old_core)
                if new_core is not None:
                    # Update core usage
                    if old_core in self._core_usage:
                        self._core_usage[old_core] = max(0, self._core_usage[old_core] - 1)
                    
                    # Set new affinity
                    if self._set_thread_affinity(thread, new_core):
                        migrated += 1
                        if self.verbose:
                            old_temp = self._per_core_temps.get(old_core, 0)
                            new_temp = self._per_core_temps.get(new_core, 0)
                            old_perf = self._core_performance.get(old_core, 0)
                            new_perf = self._core_performance.get(new_core, 0)
                            print(f"    [MIGRATE] Thread {thread.name} moved from core {old_core} "
                                  f"({old_temp:.1f}°C, {old_perf:.0f}MHz) to core {new_core} "
                                  f"({new_temp:.1f}°C, {new_perf:.0f}MHz)")
        
        if migrated > 0:
            self._last_migration_time = current_time
            with self._stats_lock:
                self._stats["thread_migrations"] += migrated
        
        return migrated
    
    def _thermal_monitor_loop(self) -> None:
        """Background thread that monitors CPU temperature and adjusts workers."""
        previous_temp = None
        
        while self._temp_monitor_running and not self._stop_event.is_set():
            try:
                temp = self._get_cpu_temperature()
                self._current_temp = temp
                
                # Get per-core temperatures
                if self._enable_thread_migration:
                    self._per_core_temps = self._get_per_core_temperatures()
                
                if temp is None:
                    # Can't read temperature, skip throttling
                    time.sleep(self.temp_check_interval)
                    continue
                
                # Detect temperature spike
                if previous_temp is not None:
                    temp_increase = temp - previous_temp
                    if temp_increase >= self._temp_spike_threshold:
                        if self.verbose:
                            print(f"    [THERMAL] Temperature spike detected: +{temp_increase:.1f}°C "
                                  f"({previous_temp:.1f}°C -> {temp:.1f}°C)")
                        
                        # Migrate threads from hot cores to cooler cores
                        if self._enable_thread_migration:
                            migrated = self._migrate_threads_from_hot_cores()
                            if migrated > 0 and self.verbose:
                                print(f"    [MIGRATE] Migrated {migrated} thread(s) to cooler cores")
                
                # Periodic rebalancing: check for hot cores and migrate even without spike
                if self._enable_thread_migration and self._per_core_temps:
                    # Check every 5 temperature checks (10 seconds at 2s interval)
                    if int(time.time()) % 10 == 0:
                        migrated = self._migrate_threads_from_hot_cores()
                        if migrated > 0 and self.verbose:
                            print(f"    [REBALANCE] Migrated {migrated} thread(s) for thermal balance")
                
                # Thermal-aware backpressure: check if all threads are hot
                if self._health_monitor and self._per_core_temps:
                    all_metrics = self._health_monitor.get_all_metrics()
                    if all_metrics:
                        hot_count = sum(1 for m in all_metrics.values() if m.status in ["hot", "critical"])
                        total_count = len(all_metrics)
                        
                        if hot_count == total_count and total_count > 0:
                            # All threads are hot - apply system-wide backpressure
                            if temp >= self._temp_critical:
                                throttle_level = "critical"
                            elif temp >= self._temp_warning:
                                throttle_level = "severe"
                            else:
                                throttle_level = "moderate"
                            
                            # Publish SystemThrottleEvent
                            throttle_event = Event(
                                event_type=EventType.SYSTEM_THROTTLE,
                                job_id=f"throttle_{int(time.time())}",
                                payload={
                                    "level": throttle_level,
                                    "hot_threads": hot_count,
                                    "total_threads": total_count,
                                    "avg_temp": temp
                                },
                                priority=Priority.CRITICAL.value,
                                sync_dispatch=False
                            )
                            self.publish(throttle_event)
                            
                            if self.verbose:
                                print(f"    [BACKPRESSURE] All {total_count} threads hot - applying {throttle_level} backpressure")
                
                previous_temp = temp
                
                # Prioritize migration over throttling - only throttle if migration isn't helping
                with self._throttle_lock:
                    old_max = self._max_concurrent_work
                    new_max = self._max_concurrent_work
                    
                    # Check if migration is helping (are there cooler cores available?)
                    migration_available = False
                    if self._enable_thread_migration and self._per_core_temps:
                        # Check if any cores are below safe temperature
                        cooler_cores = [c for c, t in self._per_core_temps.items() if t < self._temp_safe]
                        migration_available = len(cooler_cores) > 0
                    
                    # Prioritize migration over throttling - only throttle if migration isn't available
                    if temp >= self._temp_critical:
                        if not migration_available:
                            # Critical: reduce to 25% of base workers (only if no cooler cores available)
                            new_max = max(1, int(self._base_max_workers * 0.25))
                            if new_max < old_max:
                                if self.verbose:
                                    print(f"    [THERMAL] CRITICAL: {temp:.1f}°C - No cooler cores, reducing to {new_max} concurrent workers")
                                with self._stats_lock:
                                    self._stats["thermal_throttles"] += 1
                        else:
                            # Migration available - keep workers but rely on migration
                            if self.verbose and old_max < self._base_max_workers:
                                print(f"    [THERMAL] CRITICAL: {temp:.1f}°C - Using migration instead of throttling")
                    elif temp >= self._temp_warning:
                        if not migration_available:
                            # Warning: reduce to 50% of base workers (only if no cooler cores)
                            new_max = max(1, int(self._base_max_workers * 0.5))
                            if new_max < old_max:
                                if self.verbose:
                                    print(f"    [THERMAL] WARNING: {temp:.1f}°C - No cooler cores, reducing to {new_max} concurrent workers")
                                with self._stats_lock:
                                    self._stats["thermal_throttles"] += 1
                        else:
                            # Migration available - keep workers
                            if self.verbose and old_max < self._base_max_workers:
                                print(f"    [THERMAL] WARNING: {temp:.1f}°C - Using migration instead of throttling")
                    elif temp >= self._temp_safe:
                        # Safe but warm: reduce to 75% of base workers (migration should handle this)
                        new_max = max(1, int(self._base_max_workers * 0.75))
                        if new_max < old_max and not migration_available:
                            if self.verbose:
                                print(f"    [THERMAL] WARM: {temp:.1f}°C - Reducing to {new_max} concurrent workers")
                    elif temp <= self._temp_optimal:
                        # Optimal: can use full worker count
                        new_max = self._base_max_workers
                        if new_max > old_max:
                            if self.verbose:
                                print(f"    [THERMAL] COOL: {temp:.1f}°C - Increasing to {new_max} concurrent workers")
                            with self._stats_lock:
                                self._stats["thermal_resumes"] += 1
                    else:
                        # Between safe and optimal: use 90% of base workers
                        new_max = max(1, int(self._base_max_workers * 0.9))
                    
                    # Update max concurrent work
                    self._max_concurrent_work = new_max
                    
                    # If we reduced workers significantly, add a small delay to let CPU cool
                    if old_max > new_max and (old_max - new_max) >= 2:
                        time.sleep(0.5)  # Brief pause to let temperature stabilize
                
            except Exception as e:
                if self.verbose:
                    print(f"    [ERROR] Thermal monitor exception: {e}")
            
            time.sleep(self.temp_check_interval)
    
    def start(self) -> None:
        """Start the event bus worker threads and thermal monitoring."""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Start worker threads
        for i in range(self.max_workers):
            self._executor.submit(self._worker_loop)
        
        # Start thermal monitoring if enabled
        if self.enable_thermal_throttling:
            self._temp_monitor_running = True
            self._temp_monitor_thread = threading.Thread(
                target=self._thermal_monitor_loop,
                daemon=True,
                name="ThermalMonitor"
            )
            self._temp_monitor_thread.start()
        
        # Start health monitor if enabled
        if self._health_monitor:
            self._health_monitor.start()
        
        # Start load balancer rotation if enabled
        if self._load_balancer:
            self._load_balancer.start()
        
        if self.verbose:
            temp_info = f" (thermal throttling: {'ON' if self.enable_thermal_throttling else 'OFF'})"
            print(f"  [EVENT BUS] Started with {self.max_workers} workers{temp_info}")
    
    def stop(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """
        Stop the event bus and wait for pending events.
        
        Args:
            wait: Wait for pending events to complete
            timeout: Maximum time to wait (None = wait indefinitely)
        """
        if not self._running:
            return
        
        if self.verbose:
            print(f"  [EVENT BUS] Stopping (wait={wait})...")
        
        self._stop_event.set()
        
        # Stop thermal monitoring
        if self._temp_monitor_running:
            self._temp_monitor_running = False
            if self._temp_monitor_thread and self._temp_monitor_thread.is_alive():
                self._temp_monitor_thread.join(timeout=2.0)
        
        # Stop health monitor
        if self._health_monitor:
            self._health_monitor.stop()
        
        if wait:
            # Wait for all priority queues to empty
            start_wait = time.time()
            while True:
                all_empty = True
                for queue in self._priority_queues.values():
                    if not queue.empty():
                        all_empty = False
                        break
                
                # Check worker local queues
                with self._worker_queue_lock:
                    for local_queue in self._worker_local_queues.values():
                        if not local_queue.empty():
                            all_empty = False
                            break
                
                if all_empty:
                    break
                
                if timeout and (time.time() - start_wait) > timeout:
                    if self.verbose:
                        print(f"  [EVENT BUS] Timeout waiting for events")
                    break
                time.sleep(0.1)
            
            # Wait for all queues to finish processing
            for queue in self._priority_queues.values():
                queue.join()
        
        if self._executor:
            self._executor.shutdown(wait=wait)
        
        self._running = False
        
        if self.verbose:
            temp_info = ""
            if self._current_temp is not None:
                temp_info = f" (final temp: {self._current_temp:.1f}°C)"
            print(f"  [EVENT BUS] Stopped{temp_info}")
    
    def wait_for_event(
        self,
        event_type: EventType,
        job_id: str,
        timeout: Optional[float] = None
    ) -> Optional[EventResult]:
        """
        Wait for a specific event to complete.
        
        Args:
            event_type: Type of event
            job_id: Job ID
            timeout: Maximum time to wait (None = wait indefinitely)
        
        Returns:
            EventResult or None if timeout
        """
        result_key = f"{event_type.value}:{job_id}"
        start_time = time.time()
        
        while True:
            with self._results_lock:
                if result_key in self._results:
                    return self._results[result_key]
            
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            time.sleep(0.1)
    
    def wait_for_all(self, timeout: Optional[float] = None) -> None:
        """
        Wait for all events in all queues to complete with deterministic merging.
        
        Args:
            timeout: Maximum time to wait (None = wait indefinitely)
        """
        start_time = time.time()
        
        # Wait for all priority queues
        while True:
            all_empty = True
            for queue in self._priority_queues.values():
                if not queue.empty():
                    all_empty = False
                    break
            
            # Also check worker local queues
            with self._worker_queue_lock:
                for local_queue in self._worker_local_queues.values():
                    if not local_queue.empty():
                        all_empty = False
                        break
            
            if all_empty:
                break
            
            if timeout and (time.time() - start_time) > timeout:
                if self.verbose:
                    print(f"  [EVENT BUS] Timeout waiting for all events")
                break
            time.sleep(0.1)
        
        # Wait for all queues to finish processing
        for queue in self._priority_queues.values():
            queue.join()
        
        # Wait for worker local queues
        with self._worker_queue_lock:
            for local_queue in self._worker_local_queues.values():
                while not local_queue.empty():
                    time.sleep(0.01)
    
    def get_results_ordered(self) -> List[EventResult]:
        """
        Get all results in deterministic order (timestamp + job_id ordering).
        
        Returns:
            List of EventResult in deterministic order
        """
        with self._results_lock:
            return [self._results[key] for key in self._result_order if key in self._results]
    
    def get_result(
        self,
        event_type: EventType,
        job_id: str
    ) -> Optional[EventResult]:
        """
        Get result for a specific event (non-blocking).
        
        Args:
            event_type: Type of event
            job_id: Job ID
        
        Returns:
            EventResult or None if not yet processed
        """
        result_key = f"{event_type.value}:{job_id}"
        with self._results_lock:
            return self._results.get(result_key)
    
    def get_all_results(self) -> Dict[str, EventResult]:
        """Get all event results."""
        with self._results_lock:
            return self._results.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Add queue size and thermal info
        stats["queue_size"] = self._event_queue.qsize()
        stats["running"] = self._running
        with self._throttle_lock:
            stats["active_work_count"] = self._active_work_count
            stats["max_concurrent_work"] = self._max_concurrent_work
        stats["base_max_workers"] = self._base_max_workers
        stats["current_temp_c"] = self._current_temp
        stats["thermal_throttling_enabled"] = self.enable_thermal_throttling
        stats["thread_migration_enabled"] = self._enable_thread_migration
        stats["thread_migrations"] = self._stats.get("thread_migrations", 0)
        stats["priority_boosts_active"] = len(self._priority_boosts)
        with self._affinity_lock:
            stats["thread_affinities"] = len(self._thread_affinities)
            stats["core_usage"] = dict(self._core_usage)
        
        # Queue sizes
        with self._queue_locks[Priority.CRITICAL.value]:
            stats["queue_critical_size"] = self._priority_queues[Priority.CRITICAL.value].qsize()
        with self._queue_locks[Priority.HIGH.value]:
            stats["queue_high_size"] = self._priority_queues[Priority.HIGH.value].qsize()
        with self._queue_locks[Priority.NORMAL.value]:
            stats["queue_normal_size"] = self._priority_queues[Priority.NORMAL.value].qsize()
        with self._queue_locks[Priority.LOW.value]:
            stats["queue_low_size"] = self._priority_queues[Priority.LOW.value].qsize()
        
        # Worker local queue sizes
        with self._worker_queue_lock:
            stats["worker_local_queues"] = len(self._worker_local_queues)
            total_local_work = sum(q.qsize() for q in self._worker_local_queues.values())
            stats["total_local_work"] = total_local_work
        
        return stats
    
    def get_temperature(self) -> Optional[float]:
        """Get current CPU temperature in Celsius."""
        return self._current_temp
    
    def clear_results(self) -> None:
        """Clear all stored results."""
        with self._results_lock:
            self._results.clear()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop(wait=True)
    
    def _handle_work_rebalance(self, event: Event) -> EventResult:
        """
        Handle WorkRebalanceEvent - migrate tasks from hot threads to cool threads.
        
        This is called when the load balancer detects a hot thread and wants to
        rebalance work. The event bus can react by:
        - Moving queued tasks from hot thread to cool thread
        - Updating thread assignments
        """
        try:
            payload = event.payload
            from_thread = payload.get("from_thread")
            to_thread = payload.get("to_thread")
            
            if self.verbose:
                print(f"  [REBALANCE] Migrating work from {from_thread} to {to_thread}")
            
            # In a full implementation, we would:
            # 1. Find tasks queued for from_thread
            # 2. Move them to to_thread's queue
            # 3. Update thread assignments
            
            # For now, we acknowledge the rebalance
            # The actual migration happens via thread affinity changes
            
            return EventResult(
                event_type=EventType.WORK_REBALANCE,
                job_id=event.job_id,
                success=True
            )
        except Exception as e:
            if self.verbose:
                print(f"  [REBALANCE] Error handling work rebalance: {e}")
            return EventResult(
                event_type=EventType.WORK_REBALANCE,
                job_id=event.job_id,
                success=False,
                error=str(e)
            )
    
    def _handle_system_throttle(self, event: Event) -> EventResult:
        """
        Handle SystemThrottleEvent - apply system-wide thermal backpressure.
        
        When all threads are hot, we need to:
        - Slow down task intake
        - Reduce batch sizes
        - Increase sleep intervals
        """
        try:
            payload = event.payload
            throttle_level = payload.get("level", "moderate")  # "moderate", "severe", "critical"
            
            if self.verbose:
                print(f"  [THROTTLE] System-wide thermal backpressure: {throttle_level}")
            
            # Apply backpressure based on level
            with self._throttle_lock:
                if throttle_level == "critical":
                    # Reduce to 10% of workers
                    self._max_concurrent_work = max(1, int(self._base_max_workers * 0.1))
                elif throttle_level == "severe":
                    # Reduce to 25% of workers
                    self._max_concurrent_work = max(1, int(self._base_max_workers * 0.25))
                elif throttle_level == "moderate":
                    # Reduce to 50% of workers
                    self._max_concurrent_work = max(1, int(self._base_max_workers * 0.5))
            
            return EventResult(
                event_type=EventType.SYSTEM_THROTTLE,
                job_id=event.job_id,
                success=True
            )
        except Exception as e:
            if self.verbose:
                print(f"  [THROTTLE] Error handling system throttle: {e}")
            return EventResult(
                event_type=EventType.SYSTEM_THROTTLE,
                job_id=event.job_id,
                success=False,
                error=str(e)
            )


# ============================================================================
# Event-Driven Thermal Management System
# ============================================================================

@dataclass
class ThreadHealthMetrics:
    """Health metrics for a worker thread."""
    thread_id: str
    thread_name: str
    core_id: Optional[int]
    core_temp: float  # Celsius
    cpu_usage: float  # 0.0-1.0
    queue_depth: int
    avg_task_duration: float  # seconds
    stall_time: float  # seconds (time waiting for work)
    status: str  # "cool", "warm", "hot", "critical"
    timestamp: float = field(default_factory=time.time)


class ThreadHealthMonitor:
    """
    Monitors thread health and publishes ThreadHeatEvent to the event bus.
    
    Runs on a timer (50-200ms) and collects:
    - Core temperature
    - Thread CPU usage
    - Queue length
    - Average task duration
    - Stall time
    
    Then publishes ThreadHeatEvent for subscribers to react to.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        check_interval: float = 0.1,  # 100ms default
        verbose: bool = False
    ):
        """
        Initialize thread health monitor.
        
        Args:
            event_bus: Event bus to publish ThreadHeatEvent to
            check_interval: Seconds between health checks (default: 0.1 = 100ms)
            verbose: Print detailed monitoring info
        """
        self.event_bus = event_bus
        self.check_interval = check_interval
        self.verbose = verbose
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Track thread metrics
        self._thread_metrics: Dict[str, ThreadHealthMetrics] = {}
        self._metrics_lock = threading.Lock()
        
        # Track task durations per thread
        self._task_durations: Dict[str, List[float]] = {}  # thread_id -> [durations]
        self._task_start_times: Dict[str, float] = {}  # thread_id -> start_time
        
        # Temperature thresholds (from event bus)
        self._temp_critical = event_bus.max_temp_c  # 75°C
        self._temp_warning = event_bus.max_temp_c - 5.0  # 70°C
        self._temp_safe = event_bus.max_temp_c - 15.0  # 60°C
    
    def start(self) -> None:
        """Start the health monitor thread."""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        if self.verbose:
            print(f"  [HEALTH] Thread health monitor started (interval: {self.check_interval}s)")
    
    def stop(self) -> None:
        """Stop the health monitor thread."""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        if self.verbose:
            print("  [HEALTH] Thread health monitor stopped")
    
    def record_task_start(self, thread_id: str) -> None:
        """Record when a task starts processing."""
        self._task_start_times[thread_id] = time.time()
    
    def record_task_end(self, thread_id: str) -> None:
        """Record when a task finishes processing."""
        if thread_id not in self._task_start_times:
            return
        
        duration = time.time() - self._task_start_times[thread_id]
        
        with self._metrics_lock:
            if thread_id not in self._task_durations:
                self._task_durations[thread_id] = []
            self._task_durations[thread_id].append(duration)
            
            # Keep only last 10 durations for moving average
            if len(self._task_durations[thread_id]) > 10:
                self._task_durations[thread_id] = self._task_durations[thread_id][-10:]
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self._collect_and_publish_metrics()
                self._stop_event.wait(self.check_interval)
            except Exception as e:
                if self.verbose:
                    print(f"  [HEALTH] Monitor error: {e}")
                time.sleep(self.check_interval)
    
    def _collect_and_publish_metrics(self) -> None:
        """Collect metrics for all worker threads and publish ThreadHeatEvent."""
        if not PSUTIL_AVAILABLE:
            return
        
        # Get per-core temperatures
        per_core_temps = self.event_bus._get_per_core_temperatures()
        
        # Get all worker threads from event bus
        with self.event_bus._affinity_lock:
            thread_affinities = dict(self.event_bus._thread_affinities)
            worker_queues = dict(self.event_bus._worker_local_queues)
        
        # Collect metrics for each thread
        for thread, core_id in thread_affinities.items():
            thread_id = f"thread_{thread.ident}"
            thread_name = thread.name
            
            # Get core temperature
            core_temp = per_core_temps.get(core_id, 50.0) if core_id is not None else 50.0
            
            # Get CPU usage for this thread
            cpu_usage = 0.0
            try:
                thread_cpu = psutil.Process().threads()
                for t in thread_cpu:
                    if t.id == thread.ident:
                        # Get CPU percent (this is approximate)
                        cpu_usage = min(1.0, t.cpu_percent() / 100.0) if hasattr(t, 'cpu_percent') else 0.0
                        break
            except Exception:
                pass
            
            # Get queue depth
            queue_depth = 0
            if thread in worker_queues:
                queue_depth = worker_queues[thread].qsize()
            
            # Get average task duration
            avg_duration = 0.0
            with self._metrics_lock:
                if thread_id in self._task_durations and self._task_durations[thread_id]:
                    avg_duration = sum(self._task_durations[thread_id]) / len(self._task_durations[thread_id])
            
            # Calculate stall time (time since last task start)
            stall_time = 0.0
            if thread_id in self._task_start_times:
                stall_time = time.time() - self._task_start_times[thread_id]
            
            # Determine status
            if core_temp >= self._temp_critical:
                status = "critical"
            elif core_temp >= self._temp_warning:
                status = "hot"
            elif core_temp >= self._temp_safe:
                status = "warm"
            else:
                status = "cool"
            
            # Create metrics
            metrics = ThreadHealthMetrics(
                thread_id=thread_id,
                thread_name=thread_name,
                core_id=core_id,
                core_temp=core_temp,
                cpu_usage=cpu_usage,
                queue_depth=queue_depth,
                avg_task_duration=avg_duration,
                stall_time=stall_time,
                status=status
            )
            
            # Update cached metrics
            with self._metrics_lock:
                self._thread_metrics[thread_id] = metrics
            
            # Publish ThreadHeatEvent
            heat_event = Event(
                event_type=EventType.THREAD_HEAT,
                job_id=thread_id,
                payload={
                    "thread_id": thread_id,
                    "thread_name": thread_name,
                    "core_id": core_id,
                    "core_temp": core_temp,
                    "cpu_usage": cpu_usage,
                    "queue_depth": queue_depth,
                    "avg_task_duration": avg_duration,
                    "stall_time": stall_time,
                    "status": status
                },
                priority=Priority.HIGH.value,  # High priority for thermal events
                sync_dispatch=False
            )
            
            self.event_bus.publish(heat_event)
            
            if self.verbose and status in ["hot", "critical"]:
                print(f"  [HEALTH] {thread_name} ({core_id}): {core_temp:.1f}°C, {cpu_usage*100:.1f}% CPU, "
                      f"queue={queue_depth}, status={status}")
    
    def get_thread_metrics(self, thread_id: str) -> Optional[ThreadHealthMetrics]:
        """Get cached metrics for a thread."""
        with self._metrics_lock:
            return self._thread_metrics.get(thread_id)
    
    def get_all_metrics(self) -> Dict[str, ThreadHealthMetrics]:
        """Get all cached thread metrics."""
        with self._metrics_lock:
            return dict(self._thread_metrics)


class ThermalAwareLoadBalancer:
    """
    Thermal-aware load balancer with core rotation.
    
    Implements a rotating-core workload system:
    - Maintains ~50% of cores in "active pool" (high performance)
    - Maintains ~50% of cores in "cooling pool" (cooling phase)
    - Rotates cores between pools based on thermal feedback
    - Distributes wear evenly across all cores
    
    Subscribes to ThreadHeatEvent and:
    - Scores all cores using weighted metrics
    - Sorts cores: top 50% → active pool, bottom 50% → cooling pool
    - Marks cooling pool threads as throttled
    - Migrates tasks from cooling pool to active pool
    - Publishes WorkRebalanceEvent
    
    Uses weighted scoring:
    score = w1*(1 - normalized_temp) + w2*(1 - cpu_usage) + w3*(1 - queue_depth_norm)
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        health_monitor: ThreadHealthMonitor,
        verbose: bool = False,
        temp_weight: float = 0.5,  # Weight for temperature in scoring
        cpu_weight: float = 0.3,    # Weight for CPU usage in scoring
        queue_weight: float = 0.2,  # Weight for queue depth in scoring
        active_pool_ratio: float = 0.5,  # Fraction of cores in active pool (default: 50%)
        rotation_interval: float = 0.2,  # Seconds between rotation evaluations (default: 200ms)
        target_temp: float = 65.0  # Target average core temperature (thermal budget)
    ):
        """
        Initialize thermal-aware load balancer.
        
        Args:
            event_bus: Event bus to subscribe/publish to
            health_monitor: Thread health monitor for metrics
            verbose: Print detailed rebalancing info
            temp_weight: Weight for temperature in thread scoring (default: 0.5)
            cpu_weight: Weight for CPU usage in thread scoring (default: 0.3)
            queue_weight: Weight for queue depth in thread scoring (default: 0.2)
        """
        self.event_bus = event_bus
        self.health_monitor = health_monitor
        self.verbose = verbose
        self.temp_weight = temp_weight
        self.cpu_weight = cpu_weight
        self.queue_weight = queue_weight
        self.active_pool_ratio = active_pool_ratio
        self.rotation_interval = rotation_interval
        self.target_temp = target_temp
        
        # Normalize weights
        total_weight = temp_weight + cpu_weight + queue_weight
        if total_weight > 0:
            self.temp_weight /= total_weight
            self.cpu_weight /= total_weight
            self.queue_weight /= total_weight
        
        # Core rotation state
        self._active_pool: List[str] = []  # Thread IDs in active pool
        self._cooling_pool: List[str] = []  # Thread IDs in cooling pool
        self._pool_lock = threading.Lock()
        self._last_rotation_time = 0.0
        
        # Track throttled threads (thread_id -> timestamp when throttled)
        self._throttled_threads: Dict[str, float] = {}
        self._throttle_lock = threading.Lock()
        
        # Thermal budget tracking
        self._avg_core_temp: float = 0.0
        self._temp_history: List[float] = []  # Moving average window
        
        # Rotation thread
        self._rotation_running = False
        self._rotation_thread: Optional[threading.Thread] = None
        self._rotation_stop_event = threading.Event()
        
        # Subscribe to ThreadHeatEvent
        self.event_bus.subscribe(EventType.THREAD_HEAT, self._handle_thread_heat)
        
        if self.verbose:
            print(f"  [BALANCER] Thermal-aware load balancer with core rotation initialized")
            print(f"    Active pool ratio: {active_pool_ratio*100:.0f}%")
            print(f"    Rotation interval: {rotation_interval*1000:.0f}ms")
            print(f"    Target temperature: {target_temp:.1f}°C")
            print(f"    Scoring weights: temp={self.temp_weight:.2f}, cpu={self.cpu_weight:.2f}, queue={self.queue_weight:.2f}")
    
    def start(self) -> None:
        """Start the rotation thread."""
        if self._rotation_running:
            return
        
        self._rotation_running = True
        self._rotation_stop_event.clear()
        self._rotation_thread = threading.Thread(target=self._rotation_loop, daemon=True)
        self._rotation_thread.start()
        
        if self.verbose:
            print(f"  [BALANCER] Core rotation thread started")
    
    def stop(self) -> None:
        """Stop the rotation thread."""
        if not self._rotation_running:
            return
        
        self._rotation_running = False
        self._rotation_stop_event.set()
        
        if self._rotation_thread:
            self._rotation_thread.join(timeout=2.0)
        
        if self.verbose:
            print(f"  [BALANCER] Core rotation thread stopped")
    
    def _rotation_loop(self) -> None:
        """Main rotation loop - periodically re-evaluates core pools."""
        while self._rotation_running and not self._rotation_stop_event.is_set():
            try:
                self._update_core_pools()
                self._rotation_stop_event.wait(self.rotation_interval)
            except Exception as e:
                if self.verbose:
                    print(f"  [BALANCER] Rotation loop error: {e}")
                time.sleep(self.rotation_interval)
    
    def _update_core_pools(self) -> None:
        """
        Update active and cooling pools based on current thread health.
        
        Algorithm:
        1. Score all cores
        2. Sort by score (highest = best)
        3. Top 50% → active pool
        4. Bottom 50% → cooling pool
        5. Migrate tasks from cooling pool to active pool
        """
        all_metrics = self.health_monitor.get_all_metrics()
        if not all_metrics:
            return
        
        # Score all threads
        scored_threads = []
        for thread_id, metrics in all_metrics.items():
            score = self._calculate_thread_score(thread_id, metrics, all_metrics)
            scored_threads.append((thread_id, score, metrics))
        
        # Sort by score (highest first)
        scored_threads.sort(key=lambda x: x[1], reverse=True)
        
        # Split into active and cooling pools
        total_threads = len(scored_threads)
        active_count = max(1, int(total_threads * self.active_pool_ratio))
        
        new_active_pool = [t[0] for t in scored_threads[:active_count]]
        new_cooling_pool = [t[0] for t in scored_threads[active_count:]]
        
        # Calculate average temperature for thermal budget
        if scored_threads:
            avg_temp = sum(m.core_temp for _, _, m in scored_threads) / len(scored_threads)
            self._temp_history.append(avg_temp)
            if len(self._temp_history) > 10:  # Keep last 10 readings
                self._temp_history.pop(0)
            self._avg_core_temp = sum(self._temp_history) / len(self._temp_history)
            
            # Adjust active pool ratio based on thermal budget
            if self._avg_core_temp > self.target_temp + 5.0:
                # Too hot - shrink active pool to 40%
                active_count = max(1, int(total_threads * 0.4))
                new_active_pool = [t[0] for t in scored_threads[:active_count]]
                new_cooling_pool = [t[0] for t in scored_threads[active_count:]]
                if self.verbose:
                    print(f"  [BALANCER] Thermal budget exceeded ({self._avg_core_temp:.1f}°C > {self.target_temp:.1f}°C) - shrinking active pool to {active_count}/{total_threads}")
            elif self._avg_core_temp < self.target_temp - 5.0:
                # Too cool - expand active pool to 60%
                active_count = max(1, int(total_threads * 0.6))
                new_active_pool = [t[0] for t in scored_threads[:active_count]]
                new_cooling_pool = [t[0] for t in scored_threads[active_count:]]
                if self.verbose:
                    print(f"  [BALANCER] Thermal budget underutilized ({self._avg_core_temp:.1f}°C < {self.target_temp:.1f}°C) - expanding active pool to {active_count}/{total_threads}")
        
        # Update pools
        with self._pool_lock:
            old_active = set(self._active_pool)
            old_cooling = set(self._cooling_pool)
            new_active = set(new_active_pool)
            new_cooling = set(new_cooling_pool)
            
            self._active_pool = new_active_pool
            self._cooling_pool = new_cooling_pool
        
        # Mark cooling pool threads as throttled
        with self._throttle_lock:
            for thread_id in new_cooling_pool:
                if thread_id not in self._throttled_threads:
                    self._throttled_threads[thread_id] = time.time()
            # Remove threads that moved to active pool
            for thread_id in list(self._throttled_threads.keys()):
                if thread_id in new_active_pool:
                    del self._throttled_threads[thread_id]
        
        # Migrate tasks from cooling pool to active pool
        threads_moved_to_cooling = new_cooling_pool - old_cooling
        if threads_moved_to_cooling:
            for thread_id in threads_moved_to_cooling:
                self._migrate_tasks_from_thread(thread_id, new_active_pool)
        
        if self.verbose and (old_active != new_active or old_cooling != new_cooling):
            active_temps = [m.core_temp for _, _, m in scored_threads[:active_count]]
            cooling_temps = [m.core_temp for _, _, m in scored_threads[active_count:]]
            avg_active = sum(active_temps) / len(active_temps) if active_temps else 0
            avg_cooling = sum(cooling_temps) / len(cooling_temps) if cooling_temps else 0
            print(f"  [ROTATION] Active pool: {len(new_active_pool)} threads (avg {avg_active:.1f}°C), "
                  f"Cooling pool: {len(new_cooling_pool)} threads (avg {avg_cooling:.1f}°C)")
    
    def _calculate_thread_score(
        self,
        thread_id: str,
        metrics: ThreadHealthMetrics,
        all_metrics: Dict[str, ThreadHealthMetrics]
    ) -> float:
        """
        Calculate weighted score for thread selection.
        
        score = w1*(1 - normalized_temp) + w2*(1 - cpu_usage) + w3*(1 - queue_depth_norm)
        """
        # Normalize metrics
        temps = [m.core_temp for m in all_metrics.values()]
        cpu_usages = [m.cpu_usage for m in all_metrics.values()]
        queue_depths = [m.queue_depth for m in all_metrics.values()]
        
        max_temp = max(temps) if temps else 100.0
        min_temp = min(temps) if temps else 0.0
        temp_range = max_temp - min_temp if max_temp > min_temp else 1.0
        
        max_queue = max(queue_depths) if queue_depths else 1
        queue_range = max_queue if max_queue > 0 else 1
        
        # Normalize metrics (0.0 = worst, 1.0 = best)
        norm_temp = 1.0 - ((metrics.core_temp - min_temp) / temp_range) if temp_range > 0 else 0.5
        norm_cpu = 1.0 - metrics.cpu_usage
        norm_queue = 1.0 - (metrics.queue_depth / queue_range) if queue_range > 0 else 1.0
        
        # Calculate weighted score
        score = (self.temp_weight * norm_temp +
                self.cpu_weight * norm_cpu +
                self.queue_weight * norm_queue)
        
        return score
    
    def _migrate_tasks_from_thread(self, from_thread_id: str, to_pool: List[str]) -> None:
        """Migrate tasks from a cooling thread to active pool threads."""
        if not to_pool:
            return
        
        # Find best target thread in active pool
        all_metrics = self.health_monitor.get_all_metrics()
        if not all_metrics:
            return
        
        # Score active pool threads
        active_scores = []
        for thread_id in to_pool:
            if thread_id in all_metrics:
                score = self._calculate_thread_score(thread_id, all_metrics[thread_id], all_metrics)
                active_scores.append((thread_id, score))
        
        if not active_scores:
            return
        
        # Pick best target
        active_scores.sort(key=lambda x: x[1], reverse=True)
        best_target = active_scores[0][0]
        
        # Publish WorkRebalanceEvent
        rebalance_event = Event(
            event_type=EventType.WORK_REBALANCE,
            job_id=f"rebalance_{from_thread_id}_{int(time.time())}",
            payload={
                "from_thread": from_thread_id,
                "to_thread": best_target,
                "reason": "core_rotation",
                "from_pool": "cooling",
                "to_pool": "active"
            },
            priority=Priority.HIGH.value,
            sync_dispatch=False
        )
        
        self.event_bus.publish(rebalance_event)
        
        if self.verbose:
            from_metrics = all_metrics.get(from_thread_id)
            to_metrics = all_metrics.get(best_target)
            if from_metrics and to_metrics:
                print(f"  [MIGRATE] Rotating work from {from_thread_id} ({from_metrics.core_temp:.1f}°C) "
                      f"to {best_target} ({to_metrics.core_temp:.1f}°C)")
    
    def _handle_thread_heat(self, event: Event) -> EventResult:
        """Handle ThreadHeatEvent - react to hot threads."""
        try:
            payload = event.payload
            thread_id = payload["thread_id"]
            status = payload["status"]
            core_temp = payload["core_temp"]
            
            # Mark hot/critical threads as throttled
            if status in ["hot", "critical"]:
                with self._throttle_lock:
                    self._throttled_threads[thread_id] = time.time()
                
                if self.verbose:
                    print(f"  [BALANCER] Thread {thread_id} marked as throttled (status: {status}, temp: {core_temp:.1f}°C)")
                
                # Trigger rebalancing
                self._rebalance_work(thread_id)
            else:
                # Remove from throttled list when cool
                with self._throttle_lock:
                    self._throttled_threads.pop(thread_id, None)
            
            return EventResult(
                event_type=EventType.THREAD_HEAT,
                job_id=thread_id,
                success=True
            )
        except Exception as e:
            if self.verbose:
                print(f"  [BALANCER] Error handling thread heat: {e}")
            return EventResult(
                event_type=EventType.THREAD_HEAT,
                job_id=event.job_id,
                success=False,
                error=str(e)
            )
    
    def _rebalance_work(self, hot_thread_id: str) -> None:
        """Rebalance work from hot thread to cooler threads."""
        # Get all thread metrics
        all_metrics = self.health_monitor.get_all_metrics()
        
        if not all_metrics:
            return
        
        # Find the hot thread
        hot_metrics = all_metrics.get(hot_thread_id)
        if not hot_metrics:
            return
        
        # Score all threads and find best target
        best_thread_id = self._select_coolest_thread(hot_thread_id, all_metrics)
        
        if best_thread_id and best_thread_id != hot_thread_id:
            # Publish WorkRebalanceEvent
            rebalance_event = Event(
                event_type=EventType.WORK_REBALANCE,
                job_id=f"rebalance_{hot_thread_id}_{int(time.time())}",
                payload={
                    "from_thread": hot_thread_id,
                    "to_thread": best_thread_id,
                    "reason": "thermal",
                    "hot_temp": hot_metrics.core_temp,
                    "cool_temp": all_metrics[best_thread_id].core_temp
                },
                priority=Priority.HIGH.value,
                sync_dispatch=False
            )
            
            self.event_bus.publish(rebalance_event)
            
            if self.verbose:
                print(f"  [BALANCER] Rebalancing work from {hot_thread_id} ({hot_metrics.core_temp:.1f}°C) "
                      f"to {best_thread_id} ({all_metrics[best_thread_id].core_temp:.1f}°C)")
    
    def _select_coolest_thread(self, exclude_thread_id: str, all_metrics: Dict[str, ThreadHealthMetrics]) -> Optional[str]:
        """
        Select the coolest thread using weighted scoring.
        
        score = w1*(1 - normalized_temp) + w2*(1 - cpu_usage) + w3*(1 - queue_depth_norm)
        """
        if not all_metrics:
            return None
        
        # Normalize metrics
        temps = [m.core_temp for m in all_metrics.values()]
        cpu_usages = [m.cpu_usage for m in all_metrics.values()]
        queue_depths = [m.queue_depth for m in all_metrics.values()]
        
        max_temp = max(temps) if temps else 100.0
        min_temp = min(temps) if temps else 0.0
        temp_range = max_temp - min_temp if max_temp > min_temp else 1.0
        
        max_queue = max(queue_depths) if queue_depths else 1
        queue_range = max_queue if max_queue > 0 else 1
        
        best_thread_id = None
        best_score = -1.0
        
        for thread_id, metrics in all_metrics.items():
            if thread_id == exclude_thread_id:
                continue
            
            # Skip throttled threads
            with self._throttle_lock:
                if thread_id in self._throttled_threads:
                    continue
            
            # Normalize metrics (0.0 = worst, 1.0 = best)
            norm_temp = 1.0 - ((metrics.core_temp - min_temp) / temp_range) if temp_range > 0 else 0.5
            norm_cpu = 1.0 - metrics.cpu_usage
            norm_queue = 1.0 - (metrics.queue_depth / queue_range) if queue_range > 0 else 1.0
            
            # Calculate weighted score
            score = (self.temp_weight * norm_temp +
                    self.cpu_weight * norm_cpu +
                    self.queue_weight * norm_queue)
            
            if score > best_score:
                best_score = score
                best_thread_id = thread_id
        
        return best_thread_id
    
    def is_thread_throttled(self, thread_id: str) -> bool:
        """Check if a thread is currently throttled."""
        with self._throttle_lock:
            return thread_id in self._throttled_threads
    
    def get_throttled_threads(self) -> List[str]:
        """Get list of currently throttled thread IDs."""
        with self._throttle_lock:
            return list(self._throttled_threads.keys())
    
    def is_thread_in_active_pool(self, thread_id: str) -> bool:
        """Check if a thread is in the active pool."""
        with self._pool_lock:
            return thread_id in self._active_pool
    
    def get_active_pool(self) -> List[str]:
        """Get list of thread IDs in active pool."""
        with self._pool_lock:
            return list(self._active_pool)
    
    def get_cooling_pool(self) -> List[str]:
        """Get list of thread IDs in cooling pool."""
        with self._pool_lock:
            return list(self._cooling_pool)
