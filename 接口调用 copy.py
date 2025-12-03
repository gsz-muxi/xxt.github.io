# 最简单的调用
import requests
import time
import json

def run_script_and_monitor(host, username, password, list_id, poll_interval=10):
    """
    运行脚本并监控输出的完整示例
    
    Args:
        host: 服务器地址，如 "http://154.36.158.140:5000" 或 "http://127.0.0.1:5000"
        username: 用户名
        password: 密码
        list_id: 列表ID
        poll_interval: 轮询间隔（秒）
    """
    
    # 1. 启动任务
    print("正在启动任务...")
    response = requests.post(
        f"{host}/api/run",
        json={
            "username": username,
            "password": password, 
            "list_id": list_id
        }
    )
    
    if response.status_code != 200:
        print(f"启动任务失败: {response.text}")
        return None
    
    result = response.json()
    print(f"启动成功: {result}")
    
    task_id = result.get("task_id")
    if not task_id:
        print("未获取到任务ID")
        return None
    
    print(f"任务ID: {task_id}")
    
    # 2. 监控任务状态和输出
    last_timestamp = 0
    task_completed = False
    
    try:
        while not task_completed:
            # 获取任务状态
            status_response = requests.get(f"{host}/api/status/{task_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                running = status_data.get("running", False)
                
                # 获取最新输出
                output_response = requests.get(
                    f"{host}/api/output/{task_id}/latest",
                    params={"since": last_timestamp}
                )
                
                if output_response.status_code == 200:
                    output_data = output_response.json()
                    new_outputs = output_data.get("output", [])
                    
                    # 打印新输出
                    for output_item in new_outputs:
                        output_type = output_item.get("type", "stdout")
                        content = output_item.get("content", "")
                        timestamp = output_item.get("timestamp", 0)
                        
                        # 更新最后时间戳
                        if timestamp > last_timestamp:
                            last_timestamp = timestamp
                        
                        # 根据输出类型添加前缀
                        prefix = "[输出]" if output_type == "stdout" else "[错误]"
                        print(f"{prefix} {content}")
                    
                    # 更新任务完成状态
                    if not running and not task_completed:
                        task_completed = True
                        print("\n" + "="*50)
                        print("任务执行完成!")
                        
                        # 显示最终结果
                        if status_data.get("last_result"):
                            print("执行成功!")
                        elif status_data.get("last_error"):
                            error_info = status_data.get("last_error", {})
                            print(f"执行失败: {error_info.get('stderr', '未知错误')}")
                        
                        print("="*50)
                
                else:
                    print(f"获取输出失败: {output_response.text}")
            
            else:
                print(f"获取状态失败: {status_response.text}")
                break
            
            # 如果任务还在运行，等待一段时间后继续轮询
            if not task_completed:
                time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n用户中断监控，正在停止任务...")
        stop_response = requests.post(f"{host}/api/stop/{task_id}")
        if stop_response.status_code == 200:
            print("任务已停止")
        else:
            print(f"停止任务失败: {stop_response.text}")
    
    except Exception as e:
        print(f"监控过程中发生错误: {e}")
    
    return task_id

def get_task_output_simple(host, task_id, output_type="all"):
    """
    简单获取任务输出的函数
    
    Args:
        host: 服务器地址
        task_id: 任务ID
        output_type: 输出类型，可选 "all", "stdout", "stderr"
    """
    try:
        response = requests.get(
            f"{host}/api/output/{task_id}",
            params={"type": output_type, "limit": 1000}
        )
        
        if response.status_code == 200:
            data = response.json()
            outputs = data.get("output", [])
            
            print(f"\n任务 {task_id} 的输出 (共{len(outputs)}条):")
            print("-" * 50)
            
            for item in outputs:
                output_type = item.get("type", "stdout")
                content = item.get("content", "")
                timestamp = item.get("timestamp", 0)
                time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
                
                prefix = "[输出]" if output_type == "stdout" else "[错误]"
                print(f"{time_str} {prefix} {content}")
            
            print("-" * 50)
            return outputs
        else:
            print(f"获取输出失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"获取输出时发生错误: {e}")
        return None

def get_latest_output_only(host, task_id):
    """
    仅获取最新输出的简单函数
    """
    try:
        response = requests.get(f"{host}/api/output/{task_id}/latest")
        
        if response.status_code == 200:
            data = response.json()
            outputs = data.get("output", [])
            
            if outputs:
                print(f"\n任务 {task_id} 的最新输出:")
                print("-" * 30)
                
                for item in outputs:
                    output_type = item.get("type", "stdout")
                    content = item.get("content", "")
                    prefix = "[输出]" if output_type == "stdout" else "[错误]"
                    print(f"{prefix} {content}")
                
                print("-" * 30)
            else:
                print("暂无输出")
            
            return outputs
        else:
            print(f"获取最新输出失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"获取最新输出时发生错误: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    # 服务器配置
    HOST = "http://154.36.158.140:5000"  # 远程服务器
    # HOST = "http://127.0.0.1:5000"     # 本地服务器
    
    # 账号配置
    ACCOUNTS = [
        {
            "username": "19837765338",
            "password": "Cyt2006820.", 
            "list_id": 257040405
        },
        # {
        #     "username": "16712834527",
        #     "password": "ge20040205", 
        #     "list_id": 255325225
        # }
    ]
    
    # 使用方法1: 完整监控模式
    print("=== 完整监控模式 ===")
    for account in ACCOUNTS:
        task_id = run_script_and_monitor(
            host=HOST,
            username=account["username"],
            password=account["password"],
            list_id=account["list_id"]
        )
        
        if task_id:
            print(f"任务执行完成，任务ID: {task_id}")
        
        print("\n" + "="*60 + "\n")
    
    # 使用方法2: 简单启动模式（不监控）
    print("=== 简单启动模式 ===")
    response = requests.post(
        f"{HOST}/api/run",
        json={
            "username": "19087656626",
            "password": "456456ggg", 
            "list_id": 256597724
        }
    )
    print(response.json())
    
    # 如果知道任务ID，可以单独获取输出
    if response.status_code == 200:
        result = response.json()
        task_id = result.get("task_id")
        
        if task_id:
            print(f"\n任务已启动，ID: {task_id}")
            
            # 等待一段时间后获取输出
            print("等待10秒后获取输出...")
            time.sleep(10)
            
            # 获取最新输出
            get_latest_output_only(HOST, task_id)
            
            # 或者获取所有输出
            # get_task_output_simple(HOST, task_id)