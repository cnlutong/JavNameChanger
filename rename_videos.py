import os
import re
from pathlib import Path
import time

# ===== 配置参数 =====
# 要处理的目录路径
TARGET_DIR = r"\\10.0.1.10\film\NO-FILM\J-FILM"
# 是否实际重命名文件（False为预览模式，True为重命名模式）
EXECUTE_RENAME = True
# 支持的视频文件扩展名
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}

# 预编译正则表达式以提高性能
COMPILED_PATTERNS = [
    # 标准格式：字母-数字，可选-C后缀（支持.C格式）
    re.compile(r'([A-Z]{2,6}-\d{3,4}(?:[-.]C)?)'),
    # 无连字符格式：字母数字组合，如DMAT044F
    re.compile(r'([A-Z]{2,6}\d{3,4}[A-Z]?)'),
    # 带@符号的格式：xxx@ABC-123
    re.compile(r'@([A-Z]{2,6}-\d{3,4}(?:[-.]C)?)'),
    # 带@符号的无连字符格式
    re.compile(r'@([A-Z]{2,6}\d{3,4}[A-Z]?)'),
    # 其他可能的分隔符
    re.compile(r'[._\s]([A-Z]{2,6}-\d{3,4}(?:[-.]C)?)'),
    # 其他分隔符的无连字符格式
    re.compile(r'[._\s]([A-Z]{2,6}\d{3,4}[A-Z]?)'),
]

# 预编译用于格式转换的正则表达式
NO_DASH_PATTERN = re.compile(r'^[A-Z]{2,6}\d{3,4}[A-Z]?$')
PARTS_PATTERN = re.compile(r'^([A-Z]{2,6})(\d{3,4})([A-Z]?)$')

def extract_video_code(filename):
    """
    从文件名中提取番号（优化版本）
    支持格式：{番号名}-{序号} 或 {番号名}-{序号}-C
    例如：xxxx.com@ADN-566.mp4 -> ADN-566
    """
    # 移除文件扩展名并转为大写（一次性操作）
    name_without_ext = os.path.splitext(filename)[0].upper()
    
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(name_without_ext)
        if match:
            code = match.group(1)
            # 将.C格式统一转换为-C格式
            if code.endswith('.C'):
                code = code[:-2] + '-C'
            # 处理无连字符格式，如DMAT044F -> DMAT-044F
            elif NO_DASH_PATTERN.match(code):
                # 在字母和数字之间插入连字符
                match_parts = PARTS_PATTERN.match(code)
                if match_parts:
                    prefix = match_parts.group(1)
                    number = match_parts.group(2)
                    suffix = match_parts.group(3)
                    if suffix == 'C':
                        code = f"{prefix}-{number}-C"
                    elif suffix:
                        code = f"{prefix}-{number}{suffix}"
                    else:
                        code = f"{prefix}-{number}"
            return code
    
    return None

def clean_filename(old_filename):
    """
    清理文件名，返回新的文件名
    """
    # 获取文件扩展名
    _, ext = os.path.splitext(old_filename)
    
    # 提取番号
    video_code = extract_video_code(old_filename)
    
    if video_code:
        # 如果成功提取番号，返回清理后的文件名
        return f"{video_code}{ext}"
    else:
        # 无法识别的文件名，返回None表示不处理
        return None

def rename_video_files(directory, execute_rename):
    """
    重命名指定目录下的视频文件（优化版本）
    """
    try:
        # 转换为绝对路径
        directory = os.path.abspath(directory)
        
        # 确保目录存在
        if not os.path.exists(directory):
            print(f"错误: 目录 '{directory}' 不存在")
            return
        
        # 用于统计
        total_files = 0
        processed_files = 0
        renamed_files = 0
        replaced_files = 0
        skipped_files = 0
        
        # 记录开始时间
        start_time = time.time()
        
        print("开始扫描文件...")
        
        # 遍历目录
        for root, _, files in os.walk(directory):
            # 批量过滤视频文件，减少重复的扩展名检查
            video_files = [f for f in files if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS]
            
            if not video_files:
                continue
                
            print(f"处理目录: {root} (发现 {len(video_files)} 个视频文件)")
            
            for file in video_files:
                total_files += 1
                
                # 每处理100个文件显示一次进度
                if total_files % 100 == 0:
                    elapsed = time.time() - start_time
                    print(f"已处理 {total_files} 个文件，耗时 {elapsed:.1f} 秒")
                
                old_file_path = os.path.join(root, file)
                
                try:
                    # 获取新文件名
                    new_filename = clean_filename(file)
                    
                    if new_filename is None:
                        if total_files % 50 == 0:  # 减少无关输出
                            print(f"跳过（无法识别）: {file}")
                        skipped_files += 1
                        continue
                    
                    # 如果文件名已经是正确格式，跳过
                    if file == new_filename:
                        if total_files % 50 == 0:  # 减少无关输出
                            print(f"跳过（已是正确格式）: {file}")
                        skipped_files += 1
                        continue
                    
                    new_file_path = os.path.join(root, new_filename)
                    processed_files += 1
                    
                    # 检查目标文件是否已存在
                    if os.path.exists(new_file_path):
                        # 比较文件大小，保留较大的文件
                        try:
                            old_size = os.path.getsize(old_file_path)
                            new_size = os.path.getsize(new_file_path)
                            
                            old_size_mb = old_size / (1024 * 1024)
                            new_size_mb = new_size / (1024 * 1024)
                            
                            if old_size < new_size:
                                print(f"删除小体积文件（目标文件更大）: {file} (当前:{old_size_mb:.1f}MB vs 目标:{new_size_mb:.1f}MB)")
                                if execute_rename:
                                    try:
                                        os.remove(old_file_path)
                                        print(f"已删除小体积文件: {file}")
                                        deleted_files += 1
                                    except (FileNotFoundError, OSError) as e:
                                        print(f"删除文件失败: {file} - {e}")
                                        error_files += 1
                                else:
                                    print(f"预览模式：将删除小体积文件: {file}")
                                    deleted_files += 1
                                continue
                            else:
                                if old_size == new_size:
                                    print(f"将替换（文件大小相同，保留新文件）: {file} -> {new_filename} (大小:{old_size_mb:.1f}MB)")
                                else:
                                    print(f"将替换（当前文件更大）: {file} -> {new_filename} (当前:{old_size_mb:.1f}MB vs 目标:{new_size_mb:.1f}MB)")
                                if execute_rename:
                                    # 删除较小的目标文件
                                    try:
                                        os.remove(new_file_path)
                                        print(f"已删除目标文件: {new_filename}")
                                        # 再次检查原文件是否存在
                                        if not os.path.exists(old_file_path):
                                            print(f"警告: 原文件已不存在，跳过重命名: {file}")
                                            continue
                                        replaced_files += 1
                                    except Exception as e:
                                        print(f"删除目标文件失败 {new_filename}: {str(e)}")
                                        continue
                        except OSError as e:
                            print(f"获取文件大小失败 {file}: {str(e)}")
                            continue
                    
                    if not execute_rename:
                        print(f"将重命名: {file} -> {new_filename}")
                    else:
                        # 重命名前最后检查原文件是否存在
                        if not os.path.exists(old_file_path):
                            print(f"错误: 原文件不存在，无法重命名: {file}")
                            continue
                            
                        try:
                            os.rename(old_file_path, new_file_path)
                            renamed_files += 1
                            print(f"已重命名: {file} -> {new_filename}")
                        except PermissionError:
                            print(f"权限错误: 无法重命名 {file} (文件可能被其他程序占用)")
                        except FileNotFoundError:
                            print(f"文件不存在错误: {file} (文件可能在处理过程中被移动或删除)")
                        except OSError as e:
                            if "network" in str(e).lower() or "找不到网络路径" in str(e):
                                print(f"网络路径错误: {file} - {str(e)}")
                            else:
                                print(f"系统错误: {file} - {str(e)}")
                        except Exception as e:
                            print(f"重命名文件时出错 {file}: {str(e)}")
                            
                except Exception as e:
                    print(f"处理文件时出错 {file}: {str(e)}")
        
        # 打印统计信息
        print("\n统计信息:")
        print(f"扫描到的视频文件总数: {total_files}")
        print(f"需要处理的文件数: {processed_files}")
        print(f"跳过的文件数: {skipped_files}")
        if execute_rename:
            print(f"成功重命名的文件数: {renamed_files}")
            print(f"替换的文件数: {replaced_files}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")

def main():
    if EXECUTE_RENAME:
        print(f"警告：即将重命名 {TARGET_DIR} 目录下的视频文件")
        print("重命名格式：{番号名}-{序号} 或 {番号名}-{序号}-C")
        confirm = input("确认要执行重命名操作吗？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
    else:
        print("正在执行预览模式（不会实际重命名文件）")
        print(f"目标目录: {TARGET_DIR}")
        print("重命名格式：{番号名}-{序号} 或 {番号名}-{序号}-C")
        print("支持的视频格式：", ', '.join(VIDEO_EXTENSIONS))
    
    rename_video_files(TARGET_DIR, EXECUTE_RENAME)

if __name__ == "__main__":
    main()