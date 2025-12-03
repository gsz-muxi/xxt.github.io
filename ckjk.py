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

def run_main_script_in_new_window(task_id, username, password,):
    """在新的命令窗口中运行主脚本"""
    global execution_status
    
    execution_status[task_id] = {
        "running": True,
        "last_result": None,
        "last_error": None,
        "start_time": time.time()
    }
    
    try:
        # 根据操作系统选择不同的命令
        if sys.platform == "win32":
            # Windows 系统
            cmd = [
                "cmd", "/c", "start", "cmd", "/k",
                f"python ck.py -u {username} -p {password} && echo 执行完成 && pause"
            ]
        elif sys.platform == "darwin":
            # macOS 系统
            cmd = [
                "osascript", "-e",
                f'tell app "Terminal" to do script "cd {os.getcwd()} && python main.py -u {username} -p {password} -l {list_id}"'
            ]
        else:
            # Linux 系统
            cmd = [
                "x-terminal-emulator", "-e",
                f"bash -c 'cd {os.getcwd()} && python main.py -u {username} -p {password} -l {list_id}; exec bash'"
            ]
        
        print(f"开始在新窗口中执行命令，任务ID: {task_id}")
        print(f"命令: {' '.join(cmd)}")
        
        # 执行命令打开新窗口
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=30  # 打开窗口的超时时间
        )
        
        # 由于是在新窗口中执行，我们无法直接捕获执行结果
        # 这里主要检查窗口是否成功打开
        if result.returncode == 0:
            execution_status[task_id]["last_result"] = {
                "returncode": 0,
                "stdout": "新窗口已启动，请在窗口中查看执行结果",
                "stderr": "",
                "window_opened": True
            }
            print(f"新窗口启动成功，任务ID: {task_id}")
        else:
            execution_status[task_id]["last_error"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "window_opened": False
            }
            print(f"新窗口启动失败，任务ID: {task_id}, 返回码: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "",
            "stderr": "打开新窗口超时",
            "window_opened": False
        }
        print(f"打开新窗口超时，任务ID: {task_id}")
    except Exception as e:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "window_opened": False
        }
        print(f"执行异常，任务ID: {task_id}: {e}")
    finally:
        # 注意：由于是在新窗口中执行，我们无法准确知道任务何时完成
        # 这里只是标记窗口启动过程完成
        execution_status[task_id]["running"] = False
        execution_status[task_id]["end_time"] = time.time()

def run_main_script_background(task_id, username, password, list_id):
    """后台执行版本（可选）"""
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
                "window_opened": False
            }
            print(f"命令执行成功，任务ID: {task_id}")
        else:
            execution_status[task_id]["last_error"] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "window_opened": False
            }
            print(f"命令执行失败，任务ID: {task_id}, 返回码: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "",
            "stderr": "命令执行超时",
            "window_opened": False
        }
        print(f"命令执行超时，任务ID: {task_id}")
    except Exception as e:
        execution_status[task_id]["last_error"] = {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "window_opened": False
        }
        print(f"执行异常，任务ID: {task_id}: {e}")
    finally:
        execution_status[task_id]["running"] = False
        execution_status[task_id]["end_time"] = time.time()

@app.route('/api/run', methods=['POST'])
def run_script():
    """执行脚本的API接口"""
    global execution_status
    
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
    
    # 获取执行模式，默认为新窗口模式
    use_new_window = data.get('new_window', True)
    
    # 在新线程中执行脚本
    if use_new_window:
        thread = threading.Thread(
            target=run_main_script_in_new_window,
            args=(task_id, username, password, list_id)
        )
    else:
        thread = threading.Thread(
            target=run_main_script_background,
            args=(task_id, username, password, list_id)
        )
    
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "success",
        "message": "任务已开始执行" + ("（新窗口模式）" if use_new_window else "（后台模式）"),
        "task_id": task_id,
        "new_window": use_new_window
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
            "end_time": status.get("end_time")
        }
        task_list.append(task_info)
    
    return jsonify({
        "tasks": task_list,
        "total": len(task_list)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "active_tasks": len([t for t in execution_status.values() if t["running"]])
    })

@app.route('/api/cleanup', methods=['POST'])
def cleanup_tasks():
    """清理已完成的任务记录"""
    global execution_status
    
    # 只保留最近24小时的任务记录
    cutoff_time = time.time() - 24 * 60 * 60
    initial_count = len(execution_status)
    
    execution_status = {
        task_id: status 
        for task_id, status in execution_status.items() 
        if status.get("start_time", 0) > cutoff_time or status.get("running", False)
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
    print("  POST /api/run        - 执行脚本")
    print("  GET  /api/status     - 获取所有任务状态")
    print("  GET  /api/status/<id>- 获取特定任务状态")
    print("  GET  /api/tasks      - 列出所有任务")
    print("  GET  /api/health     - 健康检查")
    print("  POST /api/cleanup    - 清理任务记录")
    print("\n执行模式:")
    print("  - 默认在新窗口中执行")
    print("  - 可通过请求体中的 'new_window': false 切换到后台模式")
    
    app.run(host='0.0.0.0', port=5000, debug=False)