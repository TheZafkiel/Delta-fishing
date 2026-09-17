"""Read a literal CONFIG dictionary without executing configuration code."""
import ast

COMMENTS = {
    'region': '水花框比例 [左, 上, 宽, 高]，相对游戏客户区；仅 region_mode=relative 时生效，F7 可设置',
    'brightness': '旧版亮度阈值；仅保留兼容，当前水花算法不使用',
    'min_pixels': '旧版最小亮像素数；仅保留兼容，当前不使用',
    'max_pixels': '旧版最大亮像素数；仅保留兼容，当前不使用',
    'confirm_frames': '连续多少帧识别到水花才提竿；增大更稳，但响应更慢',
    'scan_interval': '水花检测循环的等待间隔，单位秒；实际间隔还包含截图和计算时间',
    'bite_timeout': '放大等待结束后最多等水花多少秒，包含背景采样；超时暂停',
    'cast_settle': '抛竿等待部分，单位秒；第二次左键后已立即按住右键，与 zoom_settle 相加才是开始水花识别前的总等待',
    'catch_wait': '最后一次左键后的等待秒数，之后进入下一轮抛竿',
    'click_hold': '每次左键按住的秒数',
    'max_cycles': '每次启动最多尝试的轮数；0 为持续循环，失败轮次也计数',
    'first_click_wait': '第一次左键松开后，到第二次左键之间的等待秒数',
    'release_wait': '确认水花并松开右键后，到左键提竿之间的等待秒数',
    'final_click_wait': '左键提竿后，到最后一次左键之间的等待秒数',
    'region_mode': 'screen 使用 screen_region 屏幕绝对坐标；relative 使用 region 窗口比例，F7 框选后切换为 relative',
    'screen_region': '水花框屏幕像素 [左, 上, 宽, 高]；仅 region_mode=screen 时生效',
    'zoom_settle': '放大动画等待部分，单位秒；右键按住后的总等待为 cast_settle + zoom_settle',
    'splash_value': '旧版水花亮度参数；仅保留兼容，当前不使用',
    'splash_saturation': '旧版水花饱和度参数；仅保留兼容，当前不使用',
    'splash_min_fraction': '最大连续水花至少占识别框的面积比例；如 0.008=0.8%，调大更严格',
    'splash_max_fraction': '最大连续水花最多占识别框的面积比例；超过视为过大变化，不触发',
    'splash_growth': '最大连续水花面积至少达到近期背景最大连续亮斑面积的多少倍；调大更严格',
    'baseline_frames': '每轮开始识别前采集的背景帧数；采样期间不提竿，调大可能错过早期咬钩',
    'splash_delta': '局部相对背景的最小增亮量，0~255 灰度尺度；调大更严格，必须大于等于 1',
    'splash_noise_factor': '水面噪声倍率；动态增亮阈值取 splash_delta 与 噪声×此值 的较大者',
    'failure_region': '失败文字框比例 [左, 上, 宽, 高]，相对游戏客户区；独立于水花框，F7 不修改它',
    'failure_retry_wait': '确认“提竿过早”或“鱼已逃离”后，松开按键并等待多少秒再重新抛竿',
    'failure_scan_interval': '失败文字检测间隔秒数；连续两次命中确认，连续三次未命中解除提示去重',
}


COMMENTS.update({'detection_mode': 'float：锁定红绿漂尾后检测完全入水（默认）；splash：旧水花算法', 'float_region': '浮漂框比例 [左,上,宽,高]；包含整根彩色漂尾和上下活动范围，F7 可调整', 'float_saturation': '漂尾颜色最小饱和度 0~255；降低可识别淡色，但可能混入背景', 'float_value': '漂尾颜色最小亮度 0~255；暗处可适当降低', 'float_upper_fraction': '只使用浮漂框上方此比例寻找漂尾，排除最下方倒影；0.85=85%', 'float_red_pixels': '窄条内至少包含多少红色像素才可能是漂尾', 'float_green_pixels': '同一窄条内至少包含多少绿色像素才可能是漂尾', 'float_min_pixels': '红绿像素总数下限，用于排除杂点', 'float_min_height': '彩色漂尾最小纵向跨度，单位像素', 'float_lock_frames': '连续识别多少帧后才锁定漂尾；未锁定时不会因空画面提竿', 'float_missing_frames': '锁定后连续多少帧完全找不到漂尾才提竿；太大可能延迟，太小容易误判', 'timer_enabled': '是否启用游戏剩余时间识别与声音提醒：True 开启，False 关闭', 'timer_alert_minutes': '游戏剩余时间小于等于此分钟数时提醒，每局一次；不是脚本运行时长', 'timer_scan_interval': '倒计时读取间隔，单位秒；需连续两次合理读数才提醒', 'timer_region': '左上角倒计时数字框比例 [左,上,宽,高]；按 2560×1440 截图标定', 'bite_timeout': '动画等待结束后最多等咬钩多少秒；超时松开右键，直接重新抛竿'})


COMMENTS.update({'confirm_frames': '仅 splash 模式：连续确认水花的帧数；float 模式使用 float_missing_frames', 'region': '仅 splash 相对坐标模式：水花框 [左,上,宽,高] 比例；float 模式使用 float_region', 'screen_region': '仅 splash 屏幕坐标模式：水花框像素 [左,上,宽,高]；float 模式不使用', 'splash_min_fraction': '仅 splash 模式：最大连续水花占框面积下限；float 模式不受 2016 水花门槛影响', 'splash_growth': '仅 splash 模式：水花面积相对背景亮斑面积的增长倍率', 'baseline_frames': '仅 splash 模式：水面背景采样帧数；float 模式使用 float_lock_frames', 'float_missing_frames': '锁定后连续找不到整根彩色漂尾的帧数，默认 2；无需再叠加 confirm_frames'})


COMMENTS.update({'health_enabled': '是否启用非满血声音提醒及下一轮前长按 X：True 开启，False 关闭', 'health_region': '血量数字和血条框比例 [左,上,宽,高]；相对游戏客户区，独立于 F7 框选', 'health_scan_interval': '血量检测间隔，单位秒；检测不能确认时不当作受伤', 'health_confirm_frames': '连续多少次确认非满血才响铃并安排按 X；恢复满血也需连续确认', 'health_x_hold': '确认非满血后，下一轮第一次左键前长按 X 的秒数；同一次受伤只执行一次'})


def loads(text):
    tree = ast.parse(text.lstrip('\ufeff'), filename='config.py')
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)]
    if len(tree.body) != 1 or len(assignments) != 1:
        raise ValueError('config.py 只应包含 CONFIG = {...} 和注释')
    assignment = assignments[0]
    if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name) or assignment.targets[0].id != 'CONFIG':
        raise ValueError('配置必须使用 CONFIG = {...}')
    config = ast.literal_eval(assignment.value)
    if not isinstance(config, dict) or not all(isinstance(key, str) for key in config):
        raise ValueError('CONFIG 必须是以字符串为键的字典')
    return config


def dumps(config):
    lines = ['CONFIG = {  # 钓鱼配置：只修改参数值，保存后重启脚本生效']
    for key, value in config.items():
        comment = COMMENTS.get(key, '自定义参数；是否生效取决于脚本是否读取此项')
        lines.append('    '+repr(key)+': '+repr(value)+',  # '+comment)
    lines.append('}  # 配置结束；数组顺序请按对应注释填写')
    return '\n'.join(lines)+'\n'


def save(path, config):
    path.write_text(dumps(config), encoding='utf-8')

COMMENTS.update({
    'right_press_delay': '第二次左键松开后等待多久再按住右键，单位秒',
    'cast_settle': '按住右键后的等待第一部分；与 zoom_settle 相加后才识别漂尾，失败提示仍监测',
    'zoom_settle': '按住右键后的等待第二部分；当前 2 + 1 = 3 秒，不包含右键前的 0.25 秒',
    'state_enabled': '是否结合右侧两行操作提示区分未抛竿和钓鱼中',
    'state_region': '右侧操作提示区域，相对客户区的左、上、宽、高比例',
    'state_scan_interval': '等待漂尾时检测操作状态的间隔，单位秒；连续两次未抛竿才重新开始',
})

# Generic comments remain accurate after users change their own values.
COMMENTS.update({
    'timer_scan_interval': '倒计时读取间隔，单位秒；首次需连续三次且发生递减才能确认',
    'zoom_settle': '按住右键后的等待第二部分；与 cast_settle 相加，不包含 right_press_delay',
    'scan_interval': '漂尾或水花检测循环的等待间隔，单位秒；实际间隔还包含截图和计算时间',
    'release_wait': '确认咬钩并松开右键后，到左键提竿之间的等待秒数',
    'float_missing_frames': '锁定后连续找不到整根漂尾的帧数；无需再叠加 confirm_frames',
})
