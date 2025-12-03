# chaoxing_thread_manager_fixed.py

import threading
import subprocess
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from queue import Queue
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class ChaoxingTask:
    """超星学习任务配置"""
    # 使用配置文件或命令行参数
    config_path: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    course_list: Optional[str] = None
    speed: float = 1.0
    notopen_action: str = "retry"
    name: Optional[str] = None  # 任务名称，用于标识
    
    def __post_init__(self):
        """初始化后验证参数"""
        if not self.config_path and (not self.username or not self.password):
            raise ValueError("必须提供配置文件路径或用户名和密码")


class ChaoxingThreadManager:
    """超星线程管理器"""
    
    def __init__(self, max_threads: int = 5):
        """
        初始化线程管理器
        
        参数:
        max_threads: 最大并发线程数
        """
        self.max_threads = max_threads
        self.active_threads: List[threading.Thread] = []
        self.completed_tasks: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        
    def _run_task_in_thread(self, task: ChaoxingTask, result_queue: Queue):
        """在单个线程中执行任务"""
        try:
            # 构建命令
            cmd = [sys.executable, "main.py"]
            
            if task.config_path:
                # 使用配置文件
                cmd.extend(["-c", task.config_path])
            else:
                # 使用命令行参数
                cmd.extend(["-u", task.username])
                cmd.extend(["-p", task.password])
                
                if task.course_list:
                    cmd.extend(["-l", task.course_list])
                
                if task.speed != 1.0:
                    cmd.extend(["-s", str(task.speed)])
                
                if task.notopen_action != "retry":
                    cmd.extend(["-a", task.notopen_action])
            
            logger.info(f"开始执行任务: {task.name or (task.username if task.username else '配置文件任务')}")
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # 读取输出
            stdout, stderr = process.communicate()
            
            # 记录结果
            result = {
                'task': task,
                'returncode': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'success': process.returncode == 0,
                'timestamp': time.time()
            }
            
            # 将结果放入队列
            result_queue.put(result)
            
            logger.info(f"任务完成: {task.name or (task.username if task.username else '配置文件任务')}, 返回码: {process.returncode}")
            
        except Exception as e:
            logger.error(f"任务执行失败: {task.name or (task.username if task.username else '配置文件任务')}, 错误: {e}")
            result_queue.put({
                'task': task,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False,
                'timestamp': time.time()
            })
    
    def add_task(self, task: ChaoxingTask) -> threading.Thread:
        """添加一个任务并启动线程"""
        # 检查是否有空闲线程槽
        with self._lock:
            if len(self.active_threads) >= self.max_threads:
                raise RuntimeError(f"已达到最大线程数限制: {self.max_threads}")
            
            # 创建结果队列
            result_queue = Queue()
            
            # 创建线程
            thread_name = f"Chaoxing_{task.name or (task.username if task.username else 'config')}_{len(self.active_threads)}"
            thread = threading.Thread(
                target=self._run_task_in_thread,
                args=(task, result_queue),
                name=thread_name
            )
            
            # 添加监控函数，在线程结束后处理结果
            def thread_wrapper():
                thread.start()
                thread.join()
                
                # 处理结果
                try:
                    result = result_queue.get(timeout=5)
                    with self._lock:
                        self.completed_tasks.append(result)
                        self.active_threads.remove(thread)
                except Exception as e:
                    logger.error(f"获取结果失败: {e}")
            
            # 启动监控线程
            wrapper_thread = threading.Thread(target=thread_wrapper, name=f"Wrapper_{thread_name}")
            wrapper_thread.start()
            
            # 记录活动线程
            self.active_threads.append(thread)
            
            return thread
    
    def add_tasks(self, tasks: List[ChaoxingTask]):
        """批量添加任务"""
        threads = []
        for task in tasks:
            try:
                thread = self.add_task(task)
                threads.append(thread)
                # 可选：添加延迟避免同时启动
                time.sleep(0.5)
            except RuntimeError as e:
                logger.warning(f"无法添加任务 {task.name or (task.username if task.username else '配置文件任务')}: {e}")
        
        return threads
    
    def wait_all(self, timeout: Optional[float] = None):
        """等待所有线程完成"""
        start_time = time.time()
        
        while True:
            with self._lock:
                if not self.active_threads:
                    break
            
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"等待超时 ({timeout}秒)")
                break
            
            time.sleep(1)
        
        logger.info(f"所有任务完成，共完成 {len(self.completed_tasks)} 个任务")
    
    def get_results(self) -> List[Dict[str, Any]]:
        """获取所有任务结果"""
        with self._lock:
            return self.completed_tasks.copy()
    
    def get_success_count(self) -> int:
        """获取成功任务数"""
        with self._lock:
            return sum(1 for r in self.completed_tasks if r['success'])


# 使用示例
if __name__ == "__main__":
    # 确保当前目录有main.py
    if not Path("main.py").exists():
        logger.error("错误: 在当前目录下未找到main.py")
        logger.error("请将本脚本放在与main.py相同的目录下")
        sys.exit(1)
    
    # 创建线程管理器
    manager = ChaoxingThreadManager(max_threads=3)
    
    # 定义任务列表
    tasks = [
        # 使用命令行参数的任务
        ChaoxingTask(
            username="19903373273",
            password="bjy070616",
            course_list="254337712",
            speed=1.5,
            notopen_action="continue",
            name="用户1_任务"
        ),
        ChaoxingTask(
            username="13800138000",
            password="password123",
            course_list="198198,2151141",
            name="用户2_任务"
        ),
    ]
    
    # 检查是否有配置文件任务
    config_file = "config.ini"
    if Path(config_file).exists():
        tasks.append(
            ChaoxingTask(
                config_path=config_file,
                name="配置文件任务"
            )
        )
    else:
        logger.warning(f"未找到配置文件: {config_file}")
    
    # 添加并执行所有任务
    logger.info(f"开始执行 {len(tasks)} 个任务")
    threads = manager.add_tasks(tasks)
    
    # 等待所有任务完成
    manager.wait_all(timeout=3600)  # 最多等待1小时
    
    # 输出结果统计
    results = manager.get_results()
    logger.info("=" * 50)
    logger.info("任务执行结果统计:")
    logger.info(f"总任务数: {len(results)}")
    logger.info(f"成功数: {manager.get_success_count()}")
    logger.info(f"失败数: {len(results) - manager.get_success_count()}")
    
    # 输出每个任务的简要结果
    for i, result in enumerate(results, 1):
        task_name = result['task'].name or (result['task'].username if result['task'].username else '配置文件任务')
        status = "成功" if result['success'] else "失败"
        logger.info(f"任务 {i}: {task_name} - {status} (返回码: {result['returncode']})")
    
    logger.info("所有任务执行完毕")