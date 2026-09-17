CONFIG = {  # 钓鱼配置：只修改参数值，保存后重启脚本生效
    'region': [0.4375, 0.4027777777777778, 0.140625, 0.19444444444444445],  # 仅 splash 相对坐标模式：水花框 [左,上,宽,高] 比例；float 模式使用 float_region
    'brightness': 160,  # 旧版亮度阈值；仅保留兼容，当前水花算法不使用
    'min_pixels': 15,  # 旧版最小亮像素数；仅保留兼容，当前不使用
    'max_pixels': 8000,  # 旧版最大亮像素数；仅保留兼容，当前不使用
    'confirm_frames': 2,  # 仅 splash 模式：连续确认水花的帧数；float 模式使用 float_missing_frames
    'scan_interval': 0.1,  # 漂尾或水花检测循环的等待间隔，单位秒；实际间隔还包含截图和计算时间
    'bite_timeout': 25,  # 动画等待结束后最多等咬钩多少秒；超时松开右键，直接重新抛竿
    'cast_settle': 2.0,  # 按住右键后的等待第一部分；与 zoom_settle 相加后才识别漂尾，失败提示仍监测
    'zoom_settle': 1.0,  # 按住右键后的等待第二部分；与 cast_settle 相加，不包含 right_press_delay
    'catch_wait': 2.5,  # 最后一次左键后的等待秒数，之后进入下一轮抛竿
    'click_hold': 0.1,  # 每次左键按住的秒数
    'max_cycles': 0,  # 每次启动最多尝试的轮数；0 为持续循环，失败轮次也计数
    'first_click_wait': 0.5,  # 第一次左键松开后，到第二次左键之间的等待秒数
    'release_wait': 0.2,  # 确认咬钩并松开右键后，到左键提竿之间的等待秒数
    'final_click_wait': 2.0,  # 左键提竿后，到最后一次左键之间的等待秒数
    'region_mode': 'screen',  # screen 使用 screen_region 屏幕绝对坐标；relative 使用 region 窗口比例，F7 框选后切换为 relative
    'screen_region': [1120, 580, 360, 280],  # 仅 splash 屏幕坐标模式：水花框像素 [左,上,宽,高]；float 模式不使用
    'splash_value': 100,  # 旧版水花亮度参数；仅保留兼容，当前不使用
    'splash_saturation': 65,  # 旧版水花饱和度参数；仅保留兼容，当前不使用
    'splash_min_fraction': 0.02,  # 仅 splash 模式：最大连续水花占框面积下限；float 模式不受 2016 水花门槛影响
    'splash_max_fraction': 0.45,  # 最大连续水花最多占识别框的面积比例；超过视为过大变化，不触发
    'splash_growth': 3.0,  # 仅 splash 模式：水花面积相对背景亮斑面积的增长倍率
    'baseline_frames': 6,  # 仅 splash 模式：水面背景采样帧数；float 模式使用 float_lock_frames
    'splash_delta': 12,  # 局部相对背景的最小增亮量，0~255 灰度尺度；调大更严格，必须大于等于 1
    'splash_noise_factor': 4.0,  # 水面噪声倍率；动态增亮阈值取 splash_delta 与 噪声×此值 的较大者
    'failure_region': [0.453125, 0.5833333333333334, 0.09375, 0.08333333333333333],  # 失败文字框比例 [左, 上, 宽, 高]，相对游戏客户区；独立于水花框，F7 不修改它
    'failure_retry_wait': 3.0,  # 确认“提竿过早”或“鱼已逃离”后，松开按键并等待多少秒再重新抛竿
    'failure_scan_interval': 0.2,  # 失败文字检测间隔秒数；连续两次命中确认，连续三次未命中解除提示去重
    'detection_mode': 'float',  # float：锁定红绿漂尾后检测完全入水（默认）；splash：旧水花算法
    'float_region': [0.4375, 0.24305555555555555, 0.140625, 0.3819444444444444],  # 浮漂框比例 [左,上,宽,高]；包含整根彩色漂尾和上下活动范围，F7 可调整
    'float_saturation': 90,  # 漂尾颜色最小饱和度 0~255；降低可识别淡色，但可能混入背景
    'float_value': 40,  # 漂尾颜色最小亮度 0~255；暗处可适当降低
    'float_upper_fraction': 0.85,  # 只使用浮漂框上方此比例寻找漂尾，排除最下方倒影；0.85=85%
    'float_red_pixels': 8,  # 窄条内至少包含多少红色像素才可能是漂尾
    'float_green_pixels': 4,  # 同一窄条内至少包含多少绿色像素才可能是漂尾
    'float_min_pixels': 30,  # 红绿像素总数下限，用于排除杂点
    'float_min_height': 30,  # 彩色漂尾最小纵向跨度，单位像素
    'float_lock_frames': 3,  # 连续识别多少帧后才锁定漂尾；未锁定时不会因空画面提竿
    'float_missing_frames': 2,  # 锁定后连续找不到整根漂尾的帧数；无需再叠加 confirm_frames
    'timer_enabled': True,  # 是否启用游戏剩余时间识别与声音提醒：True 开启，False 关闭
    'timer_alert_minutes': 7,  # 游戏剩余时间小于等于此分钟数时提醒，每局一次；不是脚本运行时长
    'timer_scan_interval': 1.0,  # 倒计时读取间隔，单位秒；首次需连续三次且发生递减才能确认
    'timer_region': [0.0703125, 0.3138888888888889, 0.03125, 0.022916666666666665],  # 左上角倒计时数字框比例 [左,上,宽,高]；按 2560×1440 截图标定
    'health_enabled': True,  # 是否启用非满血声音提醒及下一轮前长按 X：True 开启，False 关闭
    'health_region': [0.046875, 0.8944444444444445, 0.1328125, 0.03611111111111111],  # 血量数字和血条框比例 [左,上,宽,高]；相对游戏客户区，独立于 F7 框选
    'health_scan_interval': 0.5,  # 血量检测间隔，单位秒；检测不能确认时不当作受伤
    'health_confirm_frames': 2,  # 连续多少次确认非满血才响铃并安排按 X；恢复满血也需连续确认
    'health_x_hold': 2.0,  # 确认非满血后，下一轮第一次左键前长按 X 的秒数；同一次受伤只执行一次
    'right_press_delay': 0.25,  # 第二次左键松开后等待多久再按住右键，单位秒
    'state_enabled': True,  # 是否结合右侧两行操作提示区分未抛竿和钓鱼中
    'state_region': [0.92578125, 0.5833333333333334, 0.07421875, 0.1597222222222222],  # 右侧操作提示区域，相对客户区的左、上、宽、高比例
    'state_scan_interval': 0.5,  # 等待漂尾时检测操作状态的间隔，单位秒；连续两次未抛竿才重新开始
}  # 配置结束；数组顺序请按对应注释填写
