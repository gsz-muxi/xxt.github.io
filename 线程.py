import subprocess
from flask import Flask, request, jsonify
import threading
import time
import os
import sys
import uuid

app = Flask(__name__)

# 存储执行状态和结果
execution_status = {}
# 存储线程对象
execution_threads = {}

def run_main_script_in_thread(task_id, username, password, list_id):
    """在新线程中运行主脚本"""
    global execution_status
    
    execution_status[task_id] = {
        "running": True,
        "last_result": None,
        "last_error": None,
        "start_time": time.time(),
        "output": []  # 用于存储实时输出
    }
    
    try:
        cmd = [
            "python", "main.py", 
            "-u", username, 
            "-p", password, 
            "-l", str(list_id)
        ]
        
        print(f"开始在新线程中执行命令，任务ID: {task_id}")
        print(f"命令: {' '.join(cmd)}")
        
        # 使用Popen来获取实时输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 读取实时输出
        def read_output():
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    execution_status[task_id]["output"].append(output.strip())
                    print(f"任务 {task_id} 输出: {output.strip()}")
            
            # 读取剩余输出
            remaining_stdout, stderr = process.communicate()
            if remaining_stdout:
                for line in remaining_stdout.split('\n'):
                    if line.strip():
                        execution_status[task_id]["output"].append(line.strip())
                        print(f"任务 {task_id} 输出: {line.strip()}")
            if stderr:
                for line in stderr.split('\n'):
                    if line.strip():
                        execution_status[task_id]["output"].append(f"错误: {line.strip()}")
                        print(f"任务 {task_id} 错误: {line.strip()}")
        
        # 启动输出读取线程
        output_thread = threading.Thread(target=read_output)
        output_thread.daemon = True
        output_thread.start()
        
        # 等待进程完成
        returncode = process.wait()
        
        execution_status[task_id]["last_result"] = {
            "returncode": returncode,
            "stdout": "\n".join(execution_status[task_id]["output"]),
            "stderr": "",
            "completed": True
        }
        
        if returncode == 0:
            print(f"命令执行成功，任务ID: {task_id}")
        else:
            execution_status[task_id]["last_error"] = {
                "returncode": returncode,
                "stdout": "\n".join(execution_status[task_id]["output"]),
                "stderr": "",
                "completed": True
            }
            print(f"命令执行失败，任务ID: {task_id}, 返回码: {returncode}")
            
    except subprocess.TimeoutExpired:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "\n".join(execution_status[task_id].get("output", [])),
            "stderr": "命令执行超时",
            "completed": False
        }
        print(f"命令执行超时，任务ID: {task_id}")
    except Exception as e:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "\n".join(execution_status[task_id].get("output", [])),
            "stderr": str(e),
            "completed": False
        }
        print(f"执行异常，任务ID: {task_id}: {e}")
    finally:
        execution_status[task_id]["running"] = False
        execution_status[task_id]["end_time"] = time.time()
        # 清理线程引用
        if task_id in execution_threads:
            del execution_threads[task_id]

def run_main_script_background(task_id, username, password, list_id):
    """后台执行版本（与原版本相同，保留用于兼容性）"""
    global execution_status
    
    execution_status[task_id] = {
        "running": True,
        "last_result": None,
        "last_error": None,
        "start_time": time.time()
    }
    
    try:
        cmd = [
            "python", "main.py", 
            "-u", username, 
            "-p", password, 
            "-l", str(list_id)
        ]
        
        print(f"开始执行命令，任务ID: {task_id}")
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            execution_status[task_id]["last_result"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "completed": True
            }
            print(f"命令执行成功，任务ID: {task_id}")
        else:
            execution_status[task_id]["last_error"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "completed": True
            }
            print(f"命令执行失败，任务ID: {task_id}, 返回码: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "",
            "stderr": "命令执行超时",
            "completed": False
        }
        print(f"命令执行超时，任务ID: {task_id}")
    except Exception as e:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "completed": False
        }
        print(f"执行异常，任务ID: {task_id}: {e}")
    finally:
        execution_status[task_id]["running"] = False
        execution_status[task_id]["end_time"] = time.time()

@app.route('/api/run', methods=['POST'])
def run_script():
    """执行脚本的API接口"""
    global execution_status, execution_threads
    
    data = request.get_json()
    
    # 验证必需参数
    required_fields = ['username', 'password', 'list_id']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"缺少必需参数: {field}"
            }), 400
    
    username = data['username']
    password = data['password']
    list_id = data['list_id']
    
    # 生成唯一任务ID
    task_id = str(uuid.uuid4())
    
    # 获取执行模式，默认为新线程模式（不再是新窗口）
    use_thread_mode = data.get('new_window', True)  # 保持参数名兼容，但实际使用线程
    
    # 在新线程中执行脚本
    if use_thread_mode:
        thread = threading.Thread(
            target=run_main_script_in_thread,
            args=(task_id, username, password, list_id)
        )
    else:
        thread = threading.Thread(
            target=run_main_script_background,
            args=(task_id, username, password, list_id)
        )
    
    thread.daemon = True
    thread.start()
    
    # 保存线程引用
    execution_threads[task_id] = thread
    
    return jsonify({
        "status": "success",
        "message": "任务已开始执行" + ("（新线程模式）" if use_thread_mode else "（后台模式）"),
        "task_id": task_id,
        "new_window": use_thread_mode  # 保持兼容性
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取所有任务执行状态的API接口"""
    return jsonify(execution_status)

@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取特定任务状态的API接口"""
    if task_id in execution_status:
        return jsonify(execution_status[task_id])
    else:
        return jsonify({
            "status": "error",
            "message": "任务ID不存在"
        }), 404

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务的API接口"""
    task_list = []
    for task_id, status in execution_status.items():
        task_info = {
            "task_id": task_id,
            "status": "running" if status["running"] else "completed",
            "start_time": status.get("start_time"),
            "end_time": status.get("end_time"),
            "has_error": status.get("last_error") is not None
        }
        task_list.append(task_info)
    
    return jsonify({
        "tasks": task_list,
        "total": len(task_list)
    })

@app.route('/api/output/<task_id>', methods=['GET'])
def get_task_output(task_id):
    """获取任务实时输出的API接口"""
    if task_id in execution_status:
        output_data = execution_status[task_id].get("output", [])
        return jsonify({
            "task_id": task_id,
            "output": output_data,
            "line_count": len(output_data)
        })
    else:
        return jsonify({
            "status": "error",
            "message": "任务ID不存在"
        }), 404

@app.route('/api/stop/<task_id>', methods=['POST'])
def stop_task(task_id):
    """停止运行中的任务"""
    global execution_status, execution_threads
    
    if task_id not in execution_status:
        return jsonify({
            "status": "error",
            "message": "任务ID不存在"
        }), 404
    
    if not execution_status[task_id]["running"]:
        return jsonify({
            "status": "error",
            "message": "任务未在运行"
        }), 400
    
    # 这里可以添加终止逻辑
    # 注意：终止外部进程比较复杂，这里只是标记状态
    execution_status[task_id]["running"] = False
    execution_status[task_id]["last_error"] = {
        "returncode": -1,
        "stdout": "",
        "stderr": "任务被用户终止",
        "completed": False
    }
    execution_status[task_id]["end_time"] = time.time()
    
    return jsonify({
        "status": "success",
        "message": "任务终止请求已发送"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "active_tasks": len([t for t in execution_status.values() if t["running"]]),
        "total_tasks": len(execution_status)
    })

@app.route('/api/cleanup', methods=['POST'])
def cleanup_tasks():
    """清理已完成的任务记录"""
    global execution_status, execution_threads
    
    # 只保留最近24小时的任务记录
    cutoff_time = time.time() - 24 * 60 * 60
    initial_count = len(execution_status)
    
    execution_status = {
        task_id: status 
        for task_id, status in execution_status.items() 
        if status.get("start_time", 0) > cutoff_time or status.get("running", False)
    }
    
    # 同时清理线程引用
    execution_threads = {
        task_id: thread 
        for task_id, thread in execution_threads.items() 
        if thread.is_alive()
    }
    
    cleaned_count = initial_count - len(execution_status)
    
    return jsonify({
        "status": "success",
        "message": f"清理了 {cleaned_count} 个旧任务记录",
        "remaining_tasks": len(execution_status)
    })

if __name__ == '__main__':
    print("启动接口服务，监听端口 5000")
    print("可用接口:")
    print("  POST /api/run          - 执行脚本")
    print("  GET  /api/status       - 获取所有任务状态")
    print("  GET  /api/status/<id>  - 获取特定任务状态")
    print("  GET  /api/tasks        - 列出所有任务")
    print("  GET  /api/output/<id>  - 获取任务实时输出")
    print("  POST /api/stop/<id>    - 停止运行中的任务")
    print("  GET  /api/health       - 健康检查")
    print("  POST /api/cleanup      - 清理任务记录")
    print("\n执行模式:")
    print("  - 默认在新线程中执行（支持实时输出）")
    print("  - 可通过请求体中的 'new_window': false 切换到简单后台模式")
    

    app.run(host='0.0.0.0', port=5000, debug=False)

