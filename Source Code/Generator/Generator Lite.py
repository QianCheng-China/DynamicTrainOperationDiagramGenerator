import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.offsetbox import OffsetImage, AnnotationBbox, VPacker, TextArea, AnchoredOffsetbox
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
import os
import re
from datetime import datetime, timedelta
from PIL import Image

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
                
                # 获取始发站的第一个发车事件
                first_depart_time = None
                first_depart_mileage = None
                start_station_name = None
                
                for e in events:
                    if e['status'] == 'depart':
                        first_depart_time = e['time']
                        first_depart_mileage = e['mileage']
                        start_station_name = e['station']
                        break
                
                if first_depart_time is not None and len(events) > 0:
                    schedules[train_id] = {
                        'model': train_model,
                        'direction': direction,
                        'color': color,
                        'events': events,
                        'first_depart_tod': first_depart_time % 1440,  # 始发站发车的当日分钟数
                        'first_depart_time': first_depart_time,  # 始发站发车的绝对分钟数
                        'first_event_time': events[0]['time'],  # 第一个事件的绝对分钟数
                        'total_duration': events[-1]['time'] - first_depart_time,
                        'start_station': start_station_name,
                        'start_station_mileage': first_depart_mileage
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
        start_tod = info['first_depart_tod']  # 始发站发车的当日分钟数
        
        search_start = sim_start - timedelta(days=duration // 1440 + 2)
        search_end = sim_end + timedelta(days=1)
        
        current_date = search_start.date()
        end_date = search_end.date()
        
        while current_date <= end_date:
            # 构造该日发车的绝对时间
            dep_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(minutes=start_tod)
            
            # 预停站开始时间：始发站发车前5分钟
            pre_start = dep_dt - timedelta(minutes=5)
            # 终到后消失时间
            inst_end = dep_dt + timedelta(minutes=duration + 5)
            
            if inst_end >= sim_start and pre_start <= sim_end:
                instances.append({
                    'train_id': train_id,
                    'info': info,
                    'depart_dt': dep_dt,  # 始发站发车时间
                    'offset_mins': (dep_dt - sim_start).total_seconds() / 60  # 相对于模拟开始的偏移
                })
            
            current_date += timedelta(days=1)
            
    return instances

def calculate_positions(instances, current_time, sim_start, max_mileage):
    positions = []
    
    Y_DOWN = 0.112
    Y_UP = -0.112
    STOP_OFF = 0.08721
    TERM_DUR = 5  # 分钟
    PRE_DEP_DUR = 5  # 分钟
    MIN_SPEED_THRESHOLD = 150
    
    # 当前相对于模拟开始的分钟数
    curr_sim_mins = (current_time - sim_start).total_seconds() / 60
    
    for inst in instances:
        info = inst['info']
        events = info['events']
        inst_depart_offset = inst['offset_mins']  # 始发站发车相对于模拟开始的偏移
        
        # 当前相对于始发站发车时间的分钟数
        # 负数表示发车前，正数表示发车后
        train_relative_to_depart = curr_sim_mins - inst_depart_offset
        
        # 1. 判断是否在生存周期内
        # 预停站开始：发车前5分钟
        if train_relative_to_depart < -PRE_DEP_DUR:
            continue
        
        # 终到后消失
        if train_relative_to_depart > info['total_duration'] + TERM_DUR:
            continue
        
        dirc = info['direction']
        base_y = Y_UP if dirc == 0 else Y_DOWN
        
        # 2. 始发前停站 (发车前5分钟内)
        if train_relative_to_depart < 0:
            pos_x = info['start_station_mileage'] / max_mileage
            positions.append({
                'train': inst['train_id'], 'x': pos_x, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'stopped', 'station': info['start_station'],
                'model': info['model']
            })
            continue
        
        # 3. 运行中或停站
        # 需要找到当前时间对应的事件
        # train_relative_to_depart: 相对于始发站发车时间
        # first_depart_time: 始发站发车事件的绝对分钟数（相对于列车自身时间轴）
        # first_event_time: 第一个事件的绝对分钟数
        
        # 计算当前在列车时间轴上的绝对分钟数
        current_train_absolute_mins = info['first_depart_time'] + train_relative_to_depart
        
        # 找到当前所在区间
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
            
        # 4. 终到处理
        if next_event is None:
            positions.append({
                'train': inst['train_id'], 'x': last_event['mileage'] / max_mileage, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'stopped', 'station': last_event['station'],
                'model': info['model']
            })
            continue
        
        # 5. 中途停站
        if last_event['status'] == 'arrive':
            positions.append({
                'train': inst['train_id'], 'x': last_event['mileage'] / max_mileage, 'y': base_y,
                'color': info['color'], 'direction': dirc, 'visible': True,
                'status': 'stopped', 'station': last_event['station'],
                'model': info['model']
            })
            continue
            
        # 6. 运行中
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

    # 停站层叠处理
    stopped = [p for p in positions if p.get('status') == 'stopped']
    running = [p for p in positions if p.get('status') == 'running']
    
    groups = {}
    for t in stopped:
        k = (t['station'], t['direction'])
        groups.setdefault(k, []).append(t)
    
    final_stopped = []
    for k, g in groups.items():
        g.sort(key=lambda x: x['train'])
        for idx, t in enumerate(g):
            off = (idx + 1) * STOP_OFF
            if t['y'] > 0: t['y'] += off
            else: t['y'] -= off
            final_stopped.append(t)
            
    return final_stopped + running

# ==========================================
# 生成图片序列
# ==========================================

def generate_frames_multi_day(instances, max_mile, station_list, start_dt, end_dt, folder_name='frames'):
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

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=300)
    
    peak_up = 0
    peak_down = 0
    
    Y_DOWN = 0.112
    Y_UP = -0.112
    
    TRAIN_IMG_ZOOM = 0.168
    LABEL_FONTSIZE = 4.2
    STATION_FONTSIZE = 7
    
    IMG_DATA_HEIGHT = (120 * TRAIN_IMG_ZOOM / 300) * (2.0 / 10.8)
    ONE_PIXEL_DATA = 1 / 300 * (2.0 / 10.8)
    label_height_data = (LABEL_FONTSIZE / 72.0) * (2.0 / 10.8)
    LABEL_OFFSET = IMG_DATA_HEIGHT / 2 + ONE_PIXEL_DATA + 1.2 * label_height_data
    
    desat_factor = 0.7
    char_height_data = (STATION_FONTSIZE / 72.0) * (2.0 / 10.8)
    
    for i in range(total_minutes + 1):
        current_time = start_dt + timedelta(minutes=i)
        
        ax.clear()
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-1.0, 1.0)
        ax.axis('off')
        
        # A. 车站线
        for x_pos, name in zip(station_x, station_names):
            ax.plot([x_pos, x_pos], [Y_UP, Y_DOWN],
                    color='#CCCCCC', linewidth=1, zorder=1)
        
        # B. 线路
        ax.axhline(y=Y_DOWN, color='#F0A8A8', linewidth=8, alpha=1.0, zorder=2)
        ax.axhline(y=Y_UP, color='#A8C8E8', linewidth=8, alpha=1.0, zorder=2)
        
        # C. 站名背景
        for x_pos, name in zip(station_x, station_names):
            clean_name = name.replace('站', '')
            text_h = len(clean_name) * char_height_data * 1.2
            text_w = char_height_data
            
            rect = Rectangle(
                (x_pos - text_w/2, -text_h/2), 
                text_w, text_h,
                facecolor='white', 
                edgecolor='none',
                zorder=10
            )
            ax.add_patch(rect)
            
        # D. 站名
        for x_pos, name in zip(station_x, station_names):
            clean_name = name.replace('站', '')
            vertical_name = '\n'.join(clean_name)
            ax.text(x_pos, 0, vertical_name, rotation=0, ha='center', va='center',
                    fontsize=STATION_FONTSIZE, color='#555555', zorder=11, 
                    fontproperties=CHINESE_FONT, linespacing=1.2)
        
        positions = calculate_positions(instances, current_time, start_dt, max_mile)
        vis_pos = [p for p in positions if p.get('visible', True)]
        
        running_up = [p for p in vis_pos if p['direction'] == 0 and p['status'] == 'running']
        running_down = [p for p in vis_pos if p['direction'] == 1 and p['status'] == 'running']
        
        cur_up_cnt = len(running_up)
        cur_down_cnt = len(running_down)
        
        peak_up = max(peak_up, cur_up_cnt)
        peak_down = max(peak_down, cur_down_cnt)
        
        time_str = current_time.strftime('%H:%M')
        date_str = current_time.strftime('%m/%d')
        
        ax.text(0.02, 0.97, "沪昆高速铁路列车运行图", transform=ax.transAxes,
                fontproperties=CHINESE_FONT, fontsize=19,
                ha='left', va='top', fontweight='bold')
        
        ax.text(0.02, 0.03, f"下行当前在线: {cur_down_cnt}  |  历史高峰: {peak_down}",
                transform=ax.transAxes, fontproperties=CHINESE_FONT, fontsize=11,
                ha='left', va='bottom', color='#FF4B4B', fontweight='bold')
        
        ax.text(0.02, 0.03 + 0.035, f"上行当前在线: {cur_up_cnt}  |  历史高峰: {peak_up}",
                transform=ax.transAxes, fontproperties=CHINESE_FONT, fontsize=11,
                ha='left', va='bottom', color='#4B8BBE', fontweight='bold')
        
        # === 修改后的时钟显示 ===
        # 1. 创建日期文本：黑体、加粗、16pt
        date_text = TextArea(date_str, textprops=dict(fontsize=16, fontweight='bold', 
                                                       fontproperties=FontProperties(family='SimHei'), color='#333333'))
        # 2. 创建时间文本：Inter/Monospace、加粗、32pt
        time_text = TextArea(time_str, textprops=dict(fontsize=32, fontweight='bold', 
                                                       color='#333333', fontfamily='monospace'))
        
        # 3. 使用 VPacker 组合，设置间距
        box = VPacker(children=[date_text, time_text], sep=9.6, align='center', pad=0)
        
        # 4. 使用 AnchoredOffsetbox 定位
        # 注意：AnchoredOffsetbox 没有 bbox 参数，我们通过 patch 设置样式
        anchored_box = AnchoredOffsetbox(loc='upper right', child=box, pad=0.4, frameon=True,
                                        bbox_to_anchor=(0.97, 0.97), bbox_transform=ax.transAxes,
                                        borderpad=0.5)
        
        # 手动设置背景框样式 (模拟之前 bbox 参数的效果)
        anchored_box.patch.set_boxstyle("round,pad=0.3")
        anchored_box.patch.set_facecolor('white')
        anchored_box.patch.set_alpha(0.9)
        anchored_box.patch.set_edgecolor('gray')
        anchored_box.patch.set_linewidth(1.5)
        
        ax.add_artist(anchored_box)

        if vis_pos:
            for p in vis_pos:
                x, y = p['x'], p['y']
                model = p['model']
                
                img = train_images.get(model)
                if img is None: img = train_images.get('CRH380B')
                
                if img:
                    imagebox = OffsetImage(img, zoom=TRAIN_IMG_ZOOM)
                    ab = AnnotationBbox(imagebox, (x, y), frameon=False, zorder=5)
                    ax.add_artist(ab)
                
                txt_y = y - LABEL_OFFSET
                train_text = p['train']
                desat_color = desaturate_color(p['color'], desat_factor)
                
                bbox = dict(
                    boxstyle='round,pad=0.15,rounding_size=0.3',
                    facecolor=desat_color, alpha=1.0,
                    edgecolor=desat_color, linewidth=0.5
                )
                
                ax.text(x, txt_y, train_text, fontsize=LABEL_FONTSIZE, ha='center',
                        va='top', fontweight='bold', color='#222222', zorder=6,
                        fontfamily='monospace', bbox=bbox)
        
        file_path = os.path.join(folder_name, f"frame_{i:04d}.png")
        fig.savefig(file_path, bbox_inches='tight', pad_inches=0.1, dpi=300)
        
        if i % 60 == 0:
            elapsed_hours = i // 60
            print(f"  进度: {i}/{total_minutes} ({time_str} {date_str}) - 已完成 {elapsed_hours} 分钟")

    plt.close(fig)
    print(f"\n✓ 全部完成！共生成 {total_minutes + 1} 张图片。")

# ==========================================
# 主程序
# ==========================================

if __name__ == "__main__":
    print("=== 列车运行图模拟系统 ===")
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
                generate_frames_multi_day(instances, max_mile, station_list, start_dt, end_dt)
