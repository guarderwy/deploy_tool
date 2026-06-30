"""部署工具 - 入口"""
import sys
import os

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from deploy_tool.app import main

if __name__ == "__main__":
    main()
