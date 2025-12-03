# 最简单的调用 - 只监控最后一行输出
import requests
import time
import json

def run_script_and_monitor_last_line(host, username, password, list_id, poll_interval=2):
    """
    运行脚本并只监控最后一行输出的简化版本
    
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
    print(f"启动成功: {result['message']}")
    
    task_id = result.get("task_id")
    if not task_id:
        print("未获取到任务ID")
        return None
    
    print(f"任务ID: {task_id}")
    print("开始监控最后一行输出...\n")
    
    # 2. 监控任务状态和最后一行输出
    last_output_line = ""
    task_completed = False
    
    try:
        while not task_completed:
            # 获取任务状态
            status_response = requests.get(f"{host}/api/status/{task_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                running = status_data.get("running", False)
                
                # 获取所有输出
                output_response = requests.get(f"{host}/api/output/{task_id}")
                
                if output_response.status_code == 200:
                    output_data = output_response.json()
                    all_outputs = output_data.get("output", [])
                    
                    # 只获取最后一行输出
                    if all_outputs:
                        last_output = all_outputs[-1]
                        current_line = last_output.get("content", "")
                        
                        # 如果最后一行发生变化，则显示
                        if current_line != last_output_line:
                            last_output_line = current_line
                            output_type = last_output.get("type", "stdout")
                            prefix = ">" if output_type == "stdout" else "![错误]"
                            print(f"{prefix} {current_line}")
                    
                    # 更新任务完成状态
                    if not running and not task_completed:
                        task_completed = True
                        print("\n" + "="*40)
                        print("任务执行完成!")
                        
                        # 显示最终结果
                        if status_data.get("last_result"):
                            print("✅ 执行成功!")
                        elif status_data.get("last_error"):
                            error_info = status_data.get("last_error", {})
                            print(f"❌ 执行失败: {error_info.get('stderr', '未知错误')}")
                        
                        print("="*40)
                
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

def get_last_line_only(host, task_id):
    """
    只获取最后一行的简单函数
    """
    try:
        response = requests.get(f"{host}/api/output/{task_id}")
        
        if response.status_code == 200:
            data = response.json()
            outputs = data.get("output", [])
            
            if outputs:
                last_output = outputs[-1]
                content = last_output.get("content", "")
                output_type = last_output.get("type", "stdout")
                
                prefix = "最后输出>" if output_type == "stdout" else "最后错误!"
                print(f"{prefix} {content}")
                
                return content
            else:
                print("暂无输出")
                return None
        else:
            print(f"获取输出失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"获取输出时发生错误: {e}")
        return None

def monitor_last_line_realtime(host, task_id, poll_interval=2):
    """
    实时监控指定任务的最后一行输出
    """
    print(f"开始实时监控任务 {task_id} 的最后一行输出...")
    print("按 Ctrl+C 停止监控\n")
    
    last_output_line = ""
    
    try:
        while True:
            # 获取任务状态
            status_response = requests.get(f"{host}/api/status/{task_id}")
            if status_response.status_code != 200:
                print("获取任务状态失败")
                break
                
            status_data = status_response.json()
            running = status_data.get("running", False)
            
            # 获取输出
            output_response = requests.get(f"{host}/api/output/{task_id}")
            if output_response.status_code == 200:
                output_data = output_response.json()
                all_outputs = output_data.get("output", [])
                
                # 只显示最后一行
                if all_outputs:
                    last_output = all_outputs[-1]
                    current_line = last_output.get("content", "")
                    
                    if current_line != last_output_line:
                        last_output_line = current_line
                        output_type = last_output.get("type", "stdout")
                        prefix = ">" if output_type == "stdout" else "![错误]"
                        print(f"{prefix} {current_line}")
            
            # 如果任务已完成，退出监控
            if not running:
                print("\n任务已完成")
                break
                
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n停止监控")
    except Exception as e:
        print(f"监控过程中发生错误: {e}")

# 使用示例
if __name__ == "__main__":
    # 服务器配置
    # HOST = "http://154.36.158.140:5000"  # 远程服务器
    HOST = "http://127.0.0.1:5000"     # 本地服务器
    
    # 账号配置
    ACCOUNTS = [
        {
            "username": "19087656626",
            "password": "456456ggg", 
            "list_id": "254596325,25659772"
        },
        # {
        #     "username": "16712834527",
        #     "password": "ge20040205", 
        #     "list_id": 255325225
        # }
    ]
    
    # 使用方法1: 完整监控模式（只显示最后一行）
    print("=== 只监控最后一行输出 ===")
    for account in ACCOUNTS:
        task_id = run_script_and_monitor_last_line(
            host=HOST,
            username=account["username"],
            password=account["password"],
            list_id=account["list_id"]
        )
        
        if task_id:
            print(f"任务执行完成，任务ID: {task_id}")
        
        print("\n" + "="*50 + "\n")
    
    # 使用方法2: 简单启动后单独监控
    print("=== 简单启动后监控 ===")
    response = requests.post(
        f"{HOST}/api/run",
        json={
            "username": "19837765338",
            "password": "Cyt2006820.", 
            "list_id": 257040405
        }
    )
    
    print(response.json())
    
    # 如果知道任务ID，可以单独监控最后一行
    if response.status_code == 200:
        result = response.json()
        task_id = result.get("task_id")
        
        if task_id:
            print(f"\n任务已启动，ID: {task_id}")
            
            # 等待一段时间后开始监控
            print("等待5秒后开始监控最后一行输出...")
            time.sleep(5)
            
            # 开始实时监控
            monitor_last_line_realtime(HOST, task_id)