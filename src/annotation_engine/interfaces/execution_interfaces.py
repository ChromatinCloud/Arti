"""
Workflow Execution Interfaces

Defines the contract for workflow execution that Person C will implement.
"""

from typing import Protocol, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .workflow_interfaces import WorkflowContext


class ExecutionStatus(str, Enum):
    """Execution status values"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CacheStatus(str, Enum):
    """Cache hit/miss status"""
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    DISABLED = "disabled"


@dataclass
class StepResult:
    """Result of executing a single processing step"""
    step_name: str
    status: ExecutionStatus
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    cache_status: CacheStatus = CacheStatus.DISABLED
    memory_peak_mb: Optional[float] = None
    output_data: Optional[Any] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if step completed successfully"""
        return self.status == ExecutionStatus.COMPLETED
    
    def set_completed(self, output_data: Any = None):
        """Mark step as completed"""
        self.status = ExecutionStatus.COMPLETED
        self.end_time = datetime.utcnow().isoformat()
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_seconds = (end - start).total_seconds()
        if output_data is not None:
            self.output_data = output_data
    
    def set_failed(self, error_message: str):
        """Mark step as failed"""
        self.status = ExecutionStatus.FAILED
        self.end_time = datetime.utcnow().isoformat()
        self.error_message = error_message


@dataclass
class PerformanceMetrics:
    """Performance metrics for workflow execution"""
    total_duration_seconds: float
    total_memory_peak_mb: float
    cache_hit_rate: float
    steps_completed: int
    steps_failed: int
    variants_processed: int
    
    # Step-by-step metrics
    step_metrics: Dict[str, StepResult] = field(default_factory=dict)
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size_mb: float = 0.0
    
    # Resource metrics
    cpu_usage_percent: Optional[float] = None
    disk_io_mb: Optional[float] = None
    network_io_mb: Optional[float] = None
    
    def add_step_result(self, step_result: StepResult):
        """Add a step result to metrics"""
        self.step_metrics[step_result.step_name] = step_result
        
        if step_result.success:
            self.steps_completed += 1
        else:
            self.steps_failed += 1
        
        # Update cache metrics
        if step_result.cache_status == CacheStatus.HIT:
            self.cache_hits += 1
        elif step_result.cache_status == CacheStatus.MISS:
            self.cache_misses += 1
    
    @property
    def cache_hit_rate_percent(self) -> float:
        """Calculate cache hit rate as percentage"""
        total_cache_ops = self.cache_hits + self.cache_misses
        if total_cache_ops == 0:
            return 0.0
        return (self.cache_hits / total_cache_ops) * 100
    
    @property
    def success_rate_percent(self) -> float:
        """Calculate step success rate as percentage"""
        total_steps = self.steps_completed + self.steps_failed
        if total_steps == 0:
            return 0.0
        return (self.steps_completed / total_steps) * 100


@dataclass 
class ExecutionResult:
    """Result of complete workflow execution"""
    execution_id: str
    status: ExecutionStatus
    start_time: str
    end_time: Optional[str] = None
    
    # Results
    annotation_results: Optional[Any] = None
    output_files: Dict[str, str] = field(default_factory=dict)
    
    # Performance data
    performance_metrics: Optional[PerformanceMetrics] = None
    
    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if execution completed successfully"""
        return self.status == ExecutionStatus.COMPLETED
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get total execution duration"""
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds()
        return None


class ProgressCallback(Protocol):
    """Callback interface for progress reporting"""
    
    def on_step_start(self, step_name: str, step_index: int, total_steps: int):
        """Called when a step starts"""
        ...
    
    def on_step_progress(self, step_name: str, progress_percent: float, message: str = ""):
        """Called during step execution for progress updates"""
        ...
    
    def on_step_complete(self, step_name: str, step_result: StepResult):
        """Called when a step completes"""
        ...
    
    def on_execution_complete(self, execution_result: ExecutionResult):
        """Called when entire execution completes"""
        ...


class CacheInterface(Protocol):
    """Interface for caching system"""
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key"""
        ...
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set cached value with optional TTL"""
        ...
    
    def invalidate(self, key: str):
        """Invalidate cached value"""
        ...
    
    def clear(self, pattern: Optional[str] = None):
        """Clear cache entries, optionally matching pattern"""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        ...


class WorkflowExecutorProtocol(Protocol):
    """
    Protocol that Person C's WorkflowExecutor must implement
    
    This defines the interface for high-performance workflow execution
    """
    
    def execute(self, 
               workflow_context: WorkflowContext,
               progress_callback: Optional[ProgressCallback] = None) -> ExecutionResult:
        """
        Execute complete workflow with performance optimization
        
        This is the main entry point for workflow execution
        """
        ...
    
    def execute_step(self, 
                    step_name: str, 
                    workflow_context: WorkflowContext,
                    previous_results: Dict[str, Any]) -> StepResult:
        """Execute a single processing step"""
        ...
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching performance statistics"""
        ...
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cached data"""
        ...
    
    def get_supported_steps(self) -> List[str]:
        """Get list of supported processing steps"""
        ...
    
    def estimate_execution_time(self, workflow_context: WorkflowContext) -> float:
        """Estimate execution time in seconds"""
        ...


class ParallelExecutorInterface(Protocol):
    """Interface for parallel execution of independent operations"""
    
    def execute_parallel(self, 
                        tasks: List[Callable],
                        max_workers: Optional[int] = None) -> List[Any]:
        """Execute multiple independent tasks in parallel"""
        ...
    
    def can_parallelize(self, step_name: str) -> bool:
        """Check if a step can be parallelized"""
        ...