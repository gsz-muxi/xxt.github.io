# -*- coding: utf-8 -*-
import argparse
import configparser
import sys
import os
import traceback
from urllib3 import disable_warnings, exceptions

from api.logger import logger
from api.base import Chaoxing, Account
from api.exceptions import LoginError, InputFormatError

# 关闭警告
disable_warnings(exceptions.InsecureRequestWarning)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Samueli924/chaoxing - 查课功能",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-c", "--config", type=str, default=None, help="使用配置文件运行程序"
    )
    parser.add_argument("-u", "--username", type=str, default=None, help="手机号账号")
    parser.add_argument("-p", "--password", type=str, default=None, help="登录密码")
    parser.add_argument(
        "-v",
        "--verbose",
        "--debug",
        action="store_true",
        help="启用调试模式, 输出DEBUG级别日志",
    )

    # 在解析之前捕获 -h 的行为
    if len(sys.argv) == 2 and sys.argv[1] in {"-h", "--help"}:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()


def load_config_from_file(config_path):
    """从配置文件加载设置"""
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf8")
    
    common_config = {}
    
    # 检查并读取common节
    if config.has_section("common"):
        common_config = dict(config.items("common"))
    
    return common_config


def build_config_from_args(args):
    """从命令行参数构建配置"""
    common_config = {
        "username": args.username,
        "password": args.password,
    }
    return common_config


def init_config():
    """初始化配置"""
    args = parse_args()
    
    if args.config:
        return load_config_from_file(args.config)
    else:
        return build_config_from_args(args)


def init_chaoxing(common_config):
    """初始化超星实例"""
    username = common_config.get("username", "")
    password = common_config.get("password", "")
    
    # 如果没有提供用户名密码，从命令行获取
    if not username or not password:
        username = input("请输入你的手机号, 按回车确认\n手机号:")
        password = input("请输入你的密码, 按回车确认\n密码:")
    
    account = Account(username, password)
    
    # 实例化超星API
    chaoxing = Chaoxing(account=account)
    
    return chaoxing


def display_course_info(course):
    """显示课程信息"""
    print(f"课程ID: {course['courseId']}")
    print(f"课程名称: {course['title']}")
    print(f"班级ID: {course['clazzId']}")
    print(f"CPI: {course['cpi']}")
    if 'teacherName' in course:
        print(f"授课教师: {course['teacherName']}")
    if 'courseCode' in course:
        print(f"课程代码: {course['courseCode']}")
    print("-" * 50)


def display_course_points(chaoxing, course):
    """显示课程章节信息"""
    print(f"\n正在获取课程 '{course['title']}' 的章节信息...")
    
    # 获取当前课程的所有章节
    point_list = chaoxing.get_course_point(
        course["courseId"], course["clazzId"], course["cpi"]
    )
    
    if not point_list or "points" not in point_list:
        print("  未找到章节信息")
        return
    
    print(f"  共找到 {len(point_list['points'])} 个章节:")
    
    for i, point in enumerate(point_list["points"], 1):
        status = "已完成" if point["has_finished"] else "未完成"
        print(f"  {i}. {point['title']} [{status}]")
        
        # 获取章节的任务点信息
        jobs, job_info = chaoxing.get_job_list(
            course["clazzId"], course["courseId"], course["cpi"], point["id"]
        )
        
        if job_info.get("notOpen", False):
            print("    * 本章节未开放")
        elif jobs:
            print(f"    * 包含 {len(jobs)} 个任务点:")
            for job in jobs:
                job_type = "视频" if job["type"] == "video" else "文档" if job["type"] == "document" else "测验" if job["type"] == "workid" else "阅读" if job["type"] == "read" else "其他"
                print(f"      - {job_type}任务: {job.get('jobid', 'N/A')}")
        else:
            print("    * 无任务点")
        
        print()


def main():
    """主程序入口 - 只保留查课功能"""
    try:
        # 初始化配置
        common_config = init_config()
        
        # 初始化超星实例
        chaoxing = init_chaoxing(common_config)
        
        # 检查当前登录状态
        _login_state = chaoxing.login()
        if not _login_state["status"]:
            raise LoginError(_login_state["msg"])
        
        print("登录成功！")
        
        # 获取所有的课程列表
        all_course = chaoxing.get_course_list()
        
        print(f"\n共找到 {len(all_course)} 门课程:")
        print("=" * 60)
        
        # 显示所有课程基本信息
        for course in all_course:
            display_course_info(course)
        
        # 询问用户是否查看详细章节信息
        while True:
            choice = input("\n是否查看某门课程的详细章节信息？(输入课程ID查看，或输入q退出): ").strip()
            
            if choice.lower() == 'q':
                break
            
            # 查找对应的课程
            selected_course = None
            for course in all_course:
                if course["courseId"] == choice:
                    selected_course = course
                    break
            
            if selected_course:
                display_course_points(chaoxing, selected_course)
            else:
                print("未找到对应的课程，请检查课程ID是否正确")
        
        print("\n查课功能结束")
        
    except SystemExit as e:
        if e.code != 0:
            logger.error(f"错误: 程序异常退出, 返回码: {e.code}")
        sys.exit(e.code)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except BaseException as e:
        print(f"错误: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        raise e


if __name__ == "__main__":
    main()