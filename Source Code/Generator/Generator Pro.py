import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.offsetbox import OffsetImage, AnnotationBbox, VPacker, HPacker, TextArea, AnchoredOffsetbox
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
import numpy as np
import os
import re
from datetime import datetime, timedelta
from PIL import Image
from collections import Counter

# ==========================================
# 字体配置
# ==========================================
CHINESE_FONT = None
for font_name in ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC', 'Arial Unicode MS']:
    try:
        CHINESE_FONT = FontProperties(family=font_name)
        test_fig, test_ax = plt.subplots()
        test_ax.text(0.5, 0.5, '测试', fontproperties=CHINESE_FONT)
        plt.close(test_fig)
        print(f"✓ 已加载中文字体: {font_name}")
        break
    except:
        continue

if CHINESE_FONT is None:
    print("⚠ 警告：未找到常用中文字体，文字可能显示为方块")
    CHINESE_FONT = FontProperties()

matplotlib.rcParams['axes.unicode_minus'] = False

# ==========================================
# 辅助函数
# ==========================================
def desaturate_color(hex_color, factor=0.7):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    r = int(r + (255 - r) * (1 - factor))
    g = int(g + (255 - g) * (1 - factor))
    b = int(b + (255 - b) * (1 - factor))
    
    return f'#{r:02x}{g:02x}{b:02x}'

def get_user_time_input(prompt):
    while True:
        try:
            time_str = input(prompt + " (格式: YYYY-MM-DD HH:MM): ")
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            print("输入格式错误，请按照 YYYY-MM-DD HH:MM 格式输入。")

# ==========================================
# 列车图像加载
# ==========================================
def load_train_images(gallery_path='gallery'):
    print(f"\n正在加载列车图库: {gallery_path}")
    train_images = {}
    if not os.path.exists(gallery_path):
        print(f"⚠ 警告：未找到图库文件夹 '{gallery_path}'")
        return train_images

    for filename in os.listdir(gallery_path):
        if filename.lower().endswith('.png'):
            model_name = filename[:-4]
            try:
                img_path = os.path.join(gallery_path, filename)
                img = Image.open(img_path).convert("RGBA")
                train_images[model_name] = img
            except Exception as e:
                print(f"  -> 加载图片失败 {filename}: {e}")
    print(f"  -> 成功加载 {len(train_images)} 种车型图片")
    return train_images

# ==========================================
# 数据读取与处理
# ==========================================

def load_station_mileage(filepath='stations.txt'):
    print(f"正在读取车站文件: {filepath}")
    try:
        df = pd.read_csv(filepath, sep=' ', header=None, encoding='utf-8-sig', names=['name', 'mileage'])
    except:
        try:
            df = pd.read_csv(filepath, sep=' ', header=None, encoding='gbk', names=['name', 'mileage'])
        except Exception as e:
            print(f"读取车站文件失败: {e}")
            return {}, 0, []
    
    station_map = {}
    station_list = []
    max_mileage = 0
    
    for _, row in df.iterrows():
        raw_name = str(row['name']).strip()
        mileage = float(row['mileage'])
        clean_name = raw_name.replace('站', '')
        station_map[raw_name] = mileage
        station_map[clean_name] = mileage
        station_list.append((raw_name, mileage))
        if mileage > max_mileage:
            max_mileage = mileage
            
    print(f"  -> 加载站点数: {len(station_map)}")
    return station_map, max_mileage, station_list

def clean_train_model(model_str):
    if not model_str: return "CRH380B"
    cleaned = model_str.replace('-', '')
    cleaned = re.sub(r'\d{4}$', '', cleaned)
    if cleaned.lower() == 'common': cleaned = 'CRH380B'
    return cleaned

def parse_timetable(filepath, station_map):
    print(f"\n正在读取列车文件: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f: lines = f.readlines()
    except:
        try:
            with open(filepath, 'r', encoding='gbk') as f: lines = f.readlines()
        except Exception as e:
            print(f"读取列车文件失败: {e}")
            return {}

    schedules = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line: i += 1; continue
            
        parts = line.split()
        if len(parts) >= 5 and parts[3].isdigit():
            train_id = parts[0]
            # 【修复】提取全程始发站和终到站
            origin_station = parts[1]
            dest_station = parts[2]
            
            num_stops = int(parts[3])
            train_model = clean_train_model(parts[4])
            
            stops_data = []
            for j in range(1, num_stops + 1):
                if i + j >= len(lines): break
                stop_line = lines[i+j].strip()
                stop_parts = stop_line.split()
                if len(stop_parts) < 4: continue
                
                s_name = stop_parts[0]
                mileage = station_map.get(s_name) or station_map.get(s_name.replace('站', ''))
                if mileage is not None:
                    stops_data.append({
                        'name': s_name, 'mileage': mileage,
                        'arr_str': stop_parts[2], 'dep_str': stop_parts[3]
                    })
            
            if len(stops_data) >= 2:
                first_mile = stops_data[0]['mileage']
                last_mile = stops_data[-1]['mileage']
                direction = 1 if last_mile > first_mile else 0
                color = '#FF4B4B' if direction == 1 else '#4B8BBE'
                
                events = []
                day_offset = 0
                prev_total_mins = -1
                
                for s in stops_data:
                    if s['arr_str'] != '0':
                        try:
                            h, m = map(int, s['arr_str'].split(':'))
                            curr_mins = h * 60 + m
                            if prev_total_mins != -1 and curr_mins < (prev_total_mins % 1440):
                                day_offset += 1
                            total_mins = day_offset * 1440 + curr_mins
                            events.append({
                                'time': total_mins, 'station': s['name'], 
                                'mileage': s['mileage'], 'status': 'arrive'
                            })
                            prev_total_mins = total_mins
                        except: pass
                    
                    if s['dep_str'] != '0':
                        try:
                            h, m = map(int, s['dep_str'].split(':'))
                            curr_mins = h * 60 + m
                            if prev_total_mins != -1 and curr_mins < (prev_total_mins % 1440):
                                day_offset += 1
                            total_mins = day_offset * 1440 + curr_mins
                            events.append({
                                'time': total_mins, 'station': s['name'], 
                                'mileage': s['mileage'], 'status': 'depart'
                            })
                            prev_total_mins = total_mins
                        except: pass
                
                first_depart_time = None
                first_depart_mileage = None
                # start_station_name 变量名改为片段始发站名，用于计算位置
                seg_start_station_name = None
                
                for e in events:
                    if e['status'] == 'depart' and first_depart_time is None:
                        first_depart_time = e['time']
                        first_depart_mileage = e['mileage']
                        seg_start_station_name = e['station']
                
                if first_depart_time is not None and len(events) > 0:
                    schedules[train_id] = {
                        'model': train_model,
                        'direction': direction,
                        'color': color,
                        'events': events,
                        'first_depart_tod': first_depart_time % 1440,
                        'first_depart_time': first_depart_time,
                        'first_event_time': events[0]['time'],
                        'total_duration': events[-1]['time'] - first_depart_time,
                        # 【修复】使用全程始发站和终到站
                        'start_station': origin_station,
                        'start_station_mileage': first_depart_mileage,
                        'end_station': dest_station
                    }
            i += num_stops + 1
        else:
            i += 1
    print(f"  -> 加载列车时刻表模板: {len(schedules)} 个车次")
    return schedules

# ==========================================
# 实例生成与位置计算
# ==========================================

def generate_train_instances(schedules, sim_start, sim_end):
    instances = []
    
    for train_id, info in schedules.items():
        duration = info['total_duration']
        start_tod = info['first_depart_tod']
        
        search_start = sim_start - timedelta(days=duration // 1440 + 2)
        search_end = sim_end + timedelta(days=1)
        
        current_date = search_start.date()
        end_date = search_end.date()
        
        while current_date <= end_date:
            dep_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(minutes=start_tod)
            pre_start = dep_dt - timedelta(minutes=5)
            inst_end = dep_dt + timedelta(minutes=duration + 5)
            
            if inst_end >= sim_start and pre_start <= sim_end:
                instances.append({
                    'train_id': train_id,
                    'info': info,
                    'depart_dt': dep_dt,
                    'offset_mins': (dep_dt - sim_start).total_seconds() / 60
                })
            
            current_date += timedelta(days=1)
            
    return instances

def calculate_positions(instances, current_time, sim_start, max_mileage, y_down_base, y_up_base):
    positions = []
    
    Y_DOWN = y_down_base
    Y_UP = y_up_base
    
    TERM_DUR = 5
    PRE_DEP_DUR = 5
    MIN_SPEED_THRESHOLD = 150
    
    curr_sim_mins = (current_time - sim_start).total_seconds() / 60
    
    for inst in instances:
        info = inst['info']
        events = info['events']
        inst_depart_offset = inst['offset_mins']
        
        train_relative_to_depart = curr_sim_mins - inst_depart_offset
        
        if train_relative_to_depart < -PRE_DEP_DUR:
            continue
        if train_relative_to_depart > info['total_duration'] + TERM_DUR:
            continue
        
        dirc = info['direction']
        base_y = Y_UP if dirc == 0 else Y_DOWN
        
        if train_relative_to_depart < 0:
            pos_x = info['start_station_mileage'] / max_mileage
            positions.append({
                'train': inst['train_id'], 'x': pos_x, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'stopped', 'station': info['start_station'],
                'model': info['model'], 'depart_time': info['first_depart_time']
            })
            continue
        
        current_train_absolute_mins = info['first_depart_time'] + train_relative_to_depart
        
        last_event = None
        next_event = None
        
        for e in events:
            if e['time'] <= current_train_absolute_mins:
                last_event = e
            if e['time'] > current_train_absolute_mins:
                next_event = e
                break
        
        if last_event is None:
            continue
            
        if next_event is None:
            positions.append({
                'train': inst['train_id'], 'x': last_event['mileage'] / max_mileage, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'stopped', 'station': last_event['station'],
                'model': info['model'], 'depart_time': info['first_depart_time']
            })
            continue
        
        if last_event['status'] == 'arrive':
            positions.append({
                'train': inst['train_id'], 'x': last_event['mileage'] / max_mileage, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'stopped', 'station': last_event['station'],
                'model': info['model'], 'depart_time': info['first_depart_time']
            })
            continue
            
        if last_event['status'] == 'depart':
            dist_km = abs(next_event['mileage'] - last_event['mileage'])
            time_dur_h = (next_event['time'] - last_event['time']) / 60.0
            
            is_abnormal = False
            if time_dur_h > 0:
                if dist_km / time_dur_h < MIN_SPEED_THRESHOLD:
                    is_abnormal = True
            
            if is_abnormal:
                continue
            
            t_total = next_event['time'] - last_event['time']
            t_passed = current_train_absolute_mins - last_event['time']
            prog = t_passed / t_total if t_total > 0 else 0
            prog = max(0.0, min(1.0, prog))
            
            cur_m = last_event['mileage'] + (next_event['mileage'] - last_event['mileage']) * prog
            positions.append({
                'train': inst['train_id'], 'x': cur_m / max_mileage, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'running',
                'model': info['model']
            })

    return positions

# ==========================================
# 车型统计信息绘制函数 (修复版 - 固定间距)
# ==========================================
def draw_model_statistics(ax, positions, train_images, y_top, x_start=-0.08):
    """
    在指定y位置显示车型统计信息
    y_top: 信息版分割线的y坐标
    """
    # 统计各车型数量
    model_counter = Counter([p['model'] for p in positions])
    
    if not model_counter:
        return

    # 参数设置
    TRAIN_IMG_ZOOM = 0.15  # 图像缩放比例
    img_height = 0.05      # 图像高度估算
    
    # 标签参数
    label_fontsize = 4.5
    # 计算标签高度（数据坐标）
    fig_height_inches = 16.0
    axes_y_range = 3.0  # -2.0 to 1.0
    label_height_data = (label_fontsize / 72.0) * (axes_y_range / fig_height_inches)
    
    img_to_label_gap = 0.01
    label_gap = 0.003
    bottom_gap = 0.02

    # ==========================================
    # 排序：按数量从多到少
    # ==========================================
    sorted_models = sorted(model_counter.items(), key=lambda x: (-x[1], x[0]))
    
    # ==========================================
    # 【关键修复】通过计算数量判断是否超过39
    # ==========================================
    if len(sorted_models) > 39:
        # 保留前38个，剩下的归入 Other
        first_38 = sorted_models[:38]
        other_count = sum(count for _, count in sorted_models[38:])
        # 重组列表，总长度为 39
        sorted_models = first_38 + [('Other', other_count)]

    # ==========================================
    # 绘制顶部分隔虚线
    # ==========================================
    # 计算起始y坐标
    y_base = y_top + bottom_gap + label_height_data + label_gap + label_height_data + img_to_label_gap + img_height / 2
    
    img_top = y_base + img_height / 2
    top_line_y = img_top + bottom_gap
    ax.axhline(y=top_line_y, color='#AAAAAA', linewidth=1, linestyle='--', zorder=20)
    
    # ==========================================
    # 使用固定间距绘制
    # ==========================================
    # 用户要求的固定间距
    train_spacing = 0.025
    
    # 绘制起始位置
    current_x = x_start
    
    for model, count in sorted_models:
        # 绘制列车图像
        img = None
        if model == 'Other':
            # 显式获取 Other 图像
            img = train_images.get('Other')
        else:
            img = train_images.get(model)
        
        # 绘制图像（如果图像不存在则跳过，但仍然绘制文字标签）
        if img:
            imagebox = OffsetImage(img, zoom=TRAIN_IMG_ZOOM)
            ab = AnnotationBbox(imagebox, (current_x, y_base), frameon=False, zorder=5)
            ax.add_artist(ab)
        
        # 计算标签位置
        img_bottom = y_base - img_height / 2
        label1_top = img_bottom - img_to_label_gap
        label1_y = label1_top  # va='top'
        
        # 第一个标签：xN
        count_text = f"x{count}"
        bbox1 = dict(boxstyle='round,pad=0.15,rounding_size=0.3', 
                    facecolor='#CCCCCC', alpha=1.0, 
                    edgecolor='#999999', linewidth=0.5)
        ax.text(current_x, label1_y, count_text, 
                fontsize=label_fontsize, ha='center', va='top', 
                fontweight='bold', color='#000000', 
                zorder=6, fontfamily='monospace', bbox=bbox1)
        
        # 第二个标签顶部
        label2_top = label1_top - label_height_data - label_gap
        label2_y = label2_top
        
        # 第二个标签：车型型号
        model_display = model[:10] # 限制长度
        bbox2 = dict(boxstyle='round,pad=0.15,rounding_size=0.3', 
                    facecolor='#AAAAAA', alpha=1.0, 
                    edgecolor='#888888', linewidth=0.5)
        ax.text(current_x, label2_y, model_display, 
                fontsize=label_fontsize, ha='center', va='top', 
                fontweight='bold', color='#000000', 
                zorder=6, fontfamily='monospace', bbox=bbox2)
        
        # 移动到下一个位置 (固定间距)
        current_x += train_spacing

# ==========================================
# 底部信息面板绘制函数
# ==========================================
def draw_bottom_info_panel(ax, all_trains, schedules, font_prop, y_min, y_top):
    """
    绘制固定列表格，包含表头：车次、始发、终到。
    """
    # 排序：direction 0(上行)在前，1(下行)在后；同方向按车次排序
    sorted_trains = sorted(all_trains, key=lambda x: (x['direction'], x['train']))
    
    # 字体改为微软雅黑
    table_font = FontProperties(family='Microsoft YaHei')
    
    # 表格布局参数
    num_cols = 7
    col_width = 1.16 / num_cols
    
    # 行高设置
    header_height = 0.06
    row_height = 0.052
    
    # 计算可用行数
    available_height = y_top - y_min - header_height
    max_rows = int(available_height / row_height)
    
    # 计算位置
    header_y = y_top
    start_y = header_y - header_height
    
    # 定义子列宽度比例
    total_units = 36.0
    train_id_units = 8.0
    start_station_units = 14.0
    end_station_units = 14.0
    
    # 计算各子列在每列中的起始位置
    train_id_x_offset = 0.0
    start_station_x_offset = train_id_units
    end_station_x_offset = train_id_units + start_station_units
    
    # 定义上下行底色
    up_bg_color = '#D6E8F5'
    down_bg_color = '#F5D6D6'
    empty_bg_color = '#FFFFFF'
    
    # ==========================================
    # 第一步：绘制所有底色（zorder=20）
    # ==========================================
    
    # 绘制表头背景
    ax.add_patch(Rectangle((-0.08, header_y - header_height), 1.16, header_height, 
                           facecolor='#E8E8E8', edgecolor='none', zorder=20))
    
    # ==========================================
    # 第二步：绘制所有分割线（zorder=25）
    # ==========================================
    
    line_width = 0.8
    
    # 水平分割线 - 表头底部
    ax.plot([-0.08, 1.08], [start_y, start_y], color='#000000', linewidth=line_width, zorder=25)
    
    # 水平分割线 - 每个数据行
    for row_idx in range(max_rows + 1):
        y_line = start_y - row_idx * row_height
        ax.plot([-0.08, 1.08], [y_line, y_line], color='#000000', linewidth=line_width, zorder=25)
    
    # 垂直分割线 - 大列之间
    for col in range(num_cols + 1):
        line_x = -0.08 + col * col_width
        ax.plot([line_x, line_x], [y_min, header_y], color='#000000', linewidth=line_width, zorder=25)
    
    # 垂直分割线 - 小列之间
    for col in range(num_cols):
        col_start_x = -0.08 + col * col_width
        
        line_x = col_start_x + (start_station_x_offset / total_units) * col_width
        ax.plot([line_x, line_x], [y_min, header_y], color='#999999', linewidth=0.5, zorder=25)
        
        line_x = col_start_x + (end_station_x_offset / total_units) * col_width
        ax.plot([line_x, line_x], [y_min, header_y], color='#999999', linewidth=0.5, zorder=25)
    
    # ==========================================
    # 第三步：绘制表头文字（zorder=26）
    # ==========================================
    for col in range(num_cols):
        col_start_x = -0.08 + col * col_width
        
        text_x = col_start_x + (train_id_x_offset / total_units) * col_width
        ax.text(text_x + 0.008, header_y - header_height/2, "车次", 
                ha='left', va='center', fontsize=6.5, fontweight='bold', 
                fontproperties=table_font, color='#333333', zorder=26)
        
        text_x = col_start_x + (start_station_x_offset / total_units) * col_width
        ax.text(text_x + 0.005, header_y - header_height/2, "始发站", 
                ha='left', va='center', fontsize=6.5, fontweight='bold', 
                fontproperties=table_font, color='#333333', zorder=26)
        
        text_x = col_start_x + (end_station_x_offset / total_units) * col_width
        ax.text(text_x + 0.005, header_y - header_height/2, "终到站", 
                ha='left', va='center', fontsize=6.5, fontweight='bold', 
                fontproperties=table_font, color='#333333', zorder=26)
    
    # ==========================================
    # 第四步：绘制列车数据（zorder=26）
    # ==========================================
    
    def format_fixed_width(text, width_en_units):
        if not text:
            text = ""
        
        current_width = 0
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                current_width += 2
            else:
                current_width += 1
        
        new_text = ""
        temp_width = 0
        for char in text:
            char_w = 2 if '\u4e00' <= char <= '\u9fff' else 1
            if temp_width + char_w <= width_en_units:
                new_text += char
                temp_width += char_w
            else:
                break
        
        return new_text
    
    for row_idx in range(max_rows):
        for col_idx in range(num_cols):
            idx = row_idx * num_cols + col_idx
            
            x_pos = -0.08 + col_idx * col_width
            y_pos = start_y - (row_idx + 1) * row_height
            
            if idx < len(sorted_trains):
                train = sorted_trains[idx]
                
                bg_color = up_bg_color if train['direction'] == 0 else down_bg_color
                
                ax.add_patch(Rectangle((x_pos, y_pos), col_width, row_height, 
                                       facecolor=bg_color, edgecolor='none', zorder=20))
                
                t_id = train['train']
                info = schedules.get(t_id, {})
                
                # 获取始发站和终到站（现在来源于parse_timetable中的全程站点）
                start_s = info.get('start_station', '?')
                end_s = info.get('end_station', '?')
                
                f_id = t_id[:6]
                f_start = format_fixed_width(start_s, 14)
                f_end = format_fixed_width(end_s, 14)
                
                status = train.get('status', 'running')
                if status == 'running':
                    dot_color = '#2ECC71'
                else:
                    dot_color = '#F1C40F'
                
                text_y = y_pos + row_height/2
                text_color = '#000000'
                
                text_x = x_pos + (train_id_x_offset / total_units) * col_width
                
                dot_x = text_x + 0.005
                ax.plot(dot_x, text_y, 'o', markersize=4, color=dot_color, zorder=27)
                
                ax.text(dot_x + 0.008, text_y, f_id, 
                        ha='left', va='center', fontsize=5.5, 
                        fontproperties=table_font, color=text_color, zorder=26)
                
                text_x = x_pos + (start_station_x_offset / total_units) * col_width
                ax.text(text_x + 0.005, text_y, f_start, 
                        ha='left', va='center', fontsize=5.5, 
                        fontproperties=table_font, color=text_color, zorder=26)
                
                text_x = x_pos + (end_station_x_offset / total_units) * col_width
                ax.text(text_x + 0.005, text_y, f_end, 
                        ha='left', va='center', fontsize=5.5, 
                        fontproperties=table_font, color=text_color, zorder=26)
            else:
                ax.add_patch(Rectangle((x_pos, y_pos), col_width, row_height, 
                                       facecolor=empty_bg_color, edgecolor='none', zorder=20))

# ==========================================
# 生成图片序列
# ==========================================

def generate_frames_multi_day(instances, max_mile, station_list, start_dt, end_dt, folder_name='frames', line_name="线路"):
    if not instances:
        print("数据为空。")
        return

    train_images = load_train_images('gallery')
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    print(f"\n图片将保存至文件夹: {folder_name}")

    delta = end_dt - start_dt
    total_minutes = int(delta.total_seconds() / 60)
    
    print(f"模拟时间范围: {start_dt} 至 {end_dt}")
    print(f"共需生成 {total_minutes + 1} 张图片...")

    unique_stations = {}
    for name, mile in station_list:
        if mile not in unique_stations:
            unique_stations[mile] = name

    station_x = [m / max_mile for m in unique_stations.keys()]
    station_names = list(unique_stations.values())

    # ==========================================
    # 布局参数
    # ==========================================
    FIG_W_INCH = 19.2
    FIG_H_INCH = 16.0
    DPI = 300
    
    AXES_Y_MIN = -2.0
    AXES_Y_MAX = 1.0
    AXES_Y_RANGE = AXES_Y_MAX - AXES_Y_MIN
    
    PT_TO_INCH = 1 / 72.0
    PT_TO_AXES = PT_TO_INCH / FIG_H_INCH
    PX_TO_DATA = (1 / DPI) * (AXES_Y_RANGE / FIG_H_INCH)
    
    # ==========================================
    # 原有元素位置计算
    # ==========================================
    
    CLOCK_TOP_MARGIN_PX = 10
    CLOCK_TOP_MARGIN_DATA = CLOCK_TOP_MARGIN_PX * PX_TO_DATA
    CLOCK_H_PT = 82.0
    CLOCK_BOTTOM_Y_AXES = 0.97 - CLOCK_H_PT * PT_TO_AXES
    
    LINE_A_Y_AXES = CLOCK_BOTTOM_Y_AXES
    LINE_A_Y_DATA = AXES_Y_MIN + AXES_Y_RANGE * LINE_A_Y_AXES
    
    STATS_FONT_SIZE = 11
    STATS_LINE_HEIGHT = 1.2
    STATS_H_PT = 2 * STATS_FONT_SIZE * STATS_LINE_HEIGHT
    STATS_H_AXES = STATS_H_PT * PT_TO_AXES
    
    STATS_BOTTOM_Y_AXES = LINE_A_Y_AXES
    STATS_TOP_Y_AXES = STATS_BOTTOM_Y_AXES + STATS_H_AXES
    
    TITLE_FONT_SIZE = 26
    TITLE_H_PT = TITLE_FONT_SIZE
    TITLE_H_AXES = TITLE_H_PT * PT_TO_AXES
    
    TITLE_BOTTOM_Y_AXES = STATS_TOP_Y_AXES + 10 * PT_TO_AXES
    TITLE_TOP_Y_AXES = TITLE_BOTTOM_Y_AXES + TITLE_H_AXES
    
    GAP_PX = 10
    GAP_DATA = GAP_PX * PX_TO_DATA
    
    TRAIN_IMG_ZOOM = 0.168
    IMG_DATA_HEIGHT = (120 * TRAIN_IMG_ZOOM / 300) * (AXES_Y_RANGE / FIG_H_INCH)
    STOP_OFF = 0.08721 * 0.8
    
    Y_DOWN_NEW = LINE_A_Y_DATA - GAP_DATA - IMG_DATA_HEIGHT/2 - 5 * STOP_OFF
    Y_UP_NEW = Y_DOWN_NEW - 0.224
    TRACK_CENTER_NEW = (Y_DOWN_NEW + Y_UP_NEW) / 2.0
    
    LABEL_FONTSIZE = 4.2
    STATION_FONTSIZE = 7
    
    label_height_data = (LABEL_FONTSIZE / 72.0) * (2.0 / 10.8)
    LABEL_OFFSET = IMG_DATA_HEIGHT / 2 + (1 / 300) * (2.0 / 10.8) + 1.2 * label_height_data
    
    desat_factor = 0.7
    char_height_data = (STATION_FONTSIZE / 72.0) * (2.0 / 10.8)
    
    # ==========================================
    # 绘图循环
    # ==========================================
    fig, ax = plt.subplots(figsize=(FIG_W_INCH, FIG_H_INCH), dpi=DPI)
    
    peak_up = 0
    peak_down = 0
    
    for i in range(total_minutes + 1):
        current_time = start_dt + timedelta(minutes=i)
        
        ax.clear()
        ax.set_xlim(-0.10, 1.10)
        ax.set_ylim(AXES_Y_MIN, AXES_Y_MAX)
        ax.axis('off')
        
        # --- 1. 绘制车站与轨道 ---
        for x_pos, name in zip(station_x, station_names):
            ax.plot([x_pos, x_pos], [Y_UP_NEW, Y_DOWN_NEW], color='#CCCCCC', linewidth=1, zorder=1)
        
        ax.axhline(y=Y_DOWN_NEW, color='#F0A8A8', linewidth=8, alpha=1.0, zorder=2)
        ax.axhline(y=Y_UP_NEW, color='#A8C8E8', linewidth=8, alpha=1.0, zorder=2)
        
        for x_pos, name in zip(station_x, station_names):
            clean_name = name.replace('站', '')
            text_h = len(clean_name) * char_height_data * 1.2
            text_w = char_height_data
            
            rect = Rectangle((x_pos - text_w/2, TRACK_CENTER_NEW - text_h/2), text_w, text_h, facecolor='white', edgecolor='none', zorder=10)
            ax.add_patch(rect)
            ax.text(x_pos, TRACK_CENTER_NEW, '\n'.join(clean_name), rotation=0, ha='center', va='center', fontsize=STATION_FONTSIZE, color='#555555', zorder=11, fontproperties=CHINESE_FONT, linespacing=1.2)
        
        # --- 2. 计算列车位置 ---
        positions = calculate_positions(instances, current_time, start_dt, max_mile, Y_DOWN_NEW, Y_UP_NEW)
        
        running_trains = [p for p in positions if p['status'] == 'running']
        stopped_trains = [p for p in positions if p['status'] == 'stopped']
        
        running_up = [p for p in running_trains if p['direction'] == 0]
        running_down = [p for p in running_trains if p['direction'] == 1]
        cur_up_cnt = len(running_up)
        cur_down_cnt = len(running_down)
        peak_up = max(peak_up, cur_up_cnt)
        peak_down = max(peak_down, cur_down_cnt)
        
        # --- 3. 绘制标题与统计信息 ---
        time_str = current_time.strftime('%H:%M')
        date_str = current_time.strftime('%m/%d')
        
        title_text = f"{line_name}列车运行略图"
        ax.text(0.02, TITLE_TOP_Y_AXES, title_text, transform=ax.transAxes, fontproperties=CHINESE_FONT, fontsize=TITLE_FONT_SIZE, ha='left', va='top', fontweight='bold')
        
        ax.text(0.02, STATS_TOP_Y_AXES, f"上行在线: {cur_up_cnt}  |  高峰在线: {peak_up}", transform=ax.transAxes, fontproperties=CHINESE_FONT, fontsize=STATS_FONT_SIZE, ha='left', va='top', color='#4B8BBE', fontweight='bold', linespacing=STATS_LINE_HEIGHT)
        
        down_line_y_axes = STATS_TOP_Y_AXES - STATS_FONT_SIZE * STATS_LINE_HEIGHT * PT_TO_AXES
        ax.text(0.02, down_line_y_axes, f"下行在线: {cur_down_cnt}  |  高峰在线: {peak_down}", transform=ax.transAxes, fontproperties=CHINESE_FONT, fontsize=STATS_FONT_SIZE, ha='left', va='top', color='#FF4B4B', fontweight='bold', linespacing=STATS_LINE_HEIGHT)
        
        # 时钟
        datetime_str = f"{date_str} {time_str}"
        datetime_text = TextArea(datetime_str, textprops=dict(fontsize=16, fontweight='bold', fontproperties=FontProperties(family='SimHei'), color='#333333'))
        
        anchored_box = AnchoredOffsetbox(loc='upper right', child=datetime_text, pad=0.4, frameon=True, bbox_to_anchor=(0.97, 0.97 - CLOCK_TOP_MARGIN_DATA), bbox_transform=ax.transAxes, borderpad=0.5)
        anchored_box.patch.set_boxstyle("round,pad=0.3,rounding_size=1.2")
        anchored_box.patch.set_facecolor('white')
        anchored_box.patch.set_alpha(0.9)
        anchored_box.patch.set_edgecolor('gray')
        anchored_box.patch.set_linewidth(1.5)
        ax.add_artist(anchored_box)

        # --- 4. 绘制列车图标 ---
        stops_by_station = {}
        for t in stopped_trains:
            key = (t['station'], t['direction'])
            stops_by_station.setdefault(key, []).append(t)
            
        for key, stops in stops_by_station.items():
            stops.sort(key=lambda x: x['depart_time'])
            num_stops = len(stops)
            
            if num_stops > 5:
                for j in range(4):
                    t = stops[j]
                    off = (j + 1) * STOP_OFF
                    y_offset = off if t['direction'] == 1 else -off
                    draw_y = t['y'] + y_offset
                    
                    img = train_images.get(t['model'])
                    if img is None: img = train_images.get('CRH380B')
                    if img:
                        imagebox = OffsetImage(img, zoom=TRAIN_IMG_ZOOM)
                        ab = AnnotationBbox(imagebox, (t['x'], draw_y), frameon=False, zorder=5)
                        ax.add_artist(ab)
                    
                    txt_y = draw_y - LABEL_OFFSET
                    desat_color = desaturate_color(t['color'], desat_factor)
                    bbox = dict(boxstyle='round,pad=0.15,rounding_size=0.3', facecolor=desat_color, alpha=1.0, edgecolor=desat_color, linewidth=0.5)
                    ax.text(t['x'], txt_y, t['train'], fontsize=LABEL_FONTSIZE, ha='center', va='top', fontweight='bold', color='#222222', zorder=6, fontfamily='monospace', bbox=bbox)
                
                t_5th = stops[4]
                off = 5 * STOP_OFF
                y_offset = off if t_5th['direction'] == 1 else -off
                draw_y = t_5th['y'] + y_offset
                
                n = num_stops - 4
                train_text = f"+{n}"
                desat_color = '#888888'
                txt_y = draw_y - LABEL_OFFSET
                bbox = dict(boxstyle='round,pad=0.15,rounding_size=0.3', facecolor=desat_color, alpha=1.0, edgecolor=desat_color, linewidth=0.5)
                ax.text(t_5th['x'], txt_y, train_text, fontsize=LABEL_FONTSIZE, ha='center', va='top', fontweight='bold', color='#222222', zorder=6, fontfamily='monospace', bbox=bbox)
            else:
                for idx, t in enumerate(stops):
                    off = (idx + 1) * STOP_OFF
                    y_offset = off if t['direction'] == 1 else -off
                    draw_y = t['y'] + y_offset

                    
                    img = train_images.get(t['model'])
                    if img is None: img = train_images.get('CRH380B')
                    if img:
                        imagebox = OffsetImage(img, zoom=TRAIN_IMG_ZOOM)
                        ab = AnnotationBbox(imagebox, (t['x'], draw_y), frameon=False, zorder=5)
                        ax.add_artist(ab)
                    
                    txt_y = draw_y - LABEL_OFFSET
                    desat_color = desaturate_color(t['color'], desat_factor)
                    bbox = dict(boxstyle='round,pad=0.15,rounding_size=0.3', facecolor=desat_color, alpha=1.0, edgecolor=desat_color, linewidth=0.5)
                    ax.text(t['x'], txt_y, t['train'], fontsize=LABEL_FONTSIZE, ha='center', va='top', fontweight='bold', color='#222222', zorder=6, fontfamily='monospace', bbox=bbox)

        for t in running_trains:
            img = train_images.get(t['model'])
            if img is None: img = train_images.get('CRH380B')
            if img:
                imagebox = OffsetImage(img, zoom=TRAIN_IMG_ZOOM)
                ab = AnnotationBbox(imagebox, (t['x'], t['y']), frameon=False, zorder=5)
                ax.add_artist(ab)
            
            txt_y = t['y'] - LABEL_OFFSET
            desat_color = desaturate_color(t['color'], desat_factor)
            bbox = dict(boxstyle='round,pad=0.15,rounding_size=0.3', facecolor=desat_color, alpha=1.0, edgecolor=desat_color, linewidth=0.5)
            ax.text(t['x'], txt_y, t['train'], fontsize=LABEL_FONTSIZE, ha='center', va='top', fontweight='bold', color='#222222', zorder=6, fontfamily='monospace', bbox=bbox)

        # ==========================================
        # 5. 绘制底部信息面板和车型统计
        # ==========================================
        panel_top_y = -0.5
        ax.axhline(y=panel_top_y, color='#AAAAAA', linewidth=1, linestyle='--', zorder=20)
        
        # 绘制车型统计信息（传入信息版分割线的y坐标）
        draw_model_statistics(ax, positions, train_images, y_top=panel_top_y)
        
        # 绘制信息版
        draw_bottom_info_panel(ax, positions, schedules, CHINESE_FONT, 
                               y_min=AXES_Y_MIN, y_top=panel_top_y)
        
        file_path = os.path.join(folder_name, f"frame_{i:04d}.png")
        fig.savefig(file_path, bbox_inches='tight', pad_inches=0.1, dpi=DPI)
        
        if i % 60 == 0:
            print(f"  进度: {i}/{total_minutes} ({time_str} {date_str})")

    plt.close(fig)
    print(f"\n✓ 全部完成！共生成 {total_minutes + 1} 张图片。")

# ==========================================
# 主程序
# ==========================================

if __name__ == "__main__":
    print("=== 列车运行图模拟系统 ===")
    
    line_name = input("请输入线路名称（例如：沪昆高速铁路，直接回车使用默认名称）: ").strip()
    if not line_name:
        line_name = "线路"
    
    start_dt = get_user_time_input("请输入开始模拟时间")
    end_dt = get_user_time_input("请输入结束模拟时间")
    
    if end_dt <= start_dt:
        print("错误：结束时间必须晚于开始时间。")
    else:
        station_map, max_mile, station_list = load_station_mileage('stations.txt')
        if station_map:
            schedules = parse_timetable('trainP.txt', station_map)
            if schedules:
                print("\n正在计算列车实例...")
                instances = generate_train_instances(schedules, start_dt, end_dt)
                print(f"  -> 活跃列车实例总数: {len(instances)}")
                generate_frames_multi_day(instances, max_mile, station_list, start_dt, end_dt, line_name=line_name)
