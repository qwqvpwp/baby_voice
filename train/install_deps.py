# -*- coding: utf-8 -*-
"""
一键安装依赖脚本
"""
import subprocess
import sys

packages = [
    "librosa>=0.10.0",
    "numpy>=1.20.0",
    "scikit-learn>=1.0.0",
    "matplotlib>=3.5.0",
    "tensorflow>=2.10.0",
    "flask>=2.0.0",
    "flask-cors>=3.0.0",
]

def install():
    print("开始安装依赖...")
    for pkg in packages:
        print(f"  安装 {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-i",
                               "https://mirrors.huaweicloud.com/repository/pypi/simple"])
    print("安装完成！")

if __name__ == "__main__":
    install()