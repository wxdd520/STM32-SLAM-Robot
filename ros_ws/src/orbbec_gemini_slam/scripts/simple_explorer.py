#!/usr/bin/env python3
"""
simple_explorer.py — STM32-SLAM-Robot 全自主探索控制器
===================================================
分工会作：ROS 只做"往哪儿走"的决策，STM32 负责底层避障安全。

算法：
  1. 从 /rtabmap/grid_map 读取占据栅格地图
  2. 找到前沿（已知空闲区域与未知区域交界处）
  3. 选最近的前沿作为目标
  4. 简单状态机：ROTATE（转向目标）→ FORWARD（前进）→ 循环
"""

import rospy
import tf2_ros
import math
import numpy as np
from collections import deque
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import Twist, PointStamped
from tf2_geometry_msgs import do_transform_point
from std_msgs.msg import UInt16

# ─── 探索参数 ─────────────────────────────────────────
EXPLORE_RATE    = 3.0       # 主循环 Hz
GOAL_TIMEOUT    = 15.0      # 目标超时 (s)，超时后重新选目标
STUCK_THRESH    = 0.05      # 卡住检测距离 (m)
ANGLE_TOLERANCE = 0.15      # 朝向容忍 (rad)，低于此值进入前进状态
GOAL_REACHED_DIST = 0.3     # 目标到达距离 (m)
FORWARD_SPEED   = 0.20      # 前进速度 m/s
TURN_SPEED      = 0.6       # 转向角速度 rad/s

# 前沿参数
FRONTIER_MIN_SIZE = 6       # 最小前沿连通区域（单元格数）
SEARCH_RADIUS     = 8.0     # 搜索半径 (m)，太远的前沿不考虑


class SimpleExplorer:
    def __init__(self):
        rospy.init_node('simple_explorer', anonymous=False)

        # ── 订阅 ──
        self.map_sub = rospy.Subscriber('/rtabmap/grid_map', OccupancyGrid,
                                        self.map_cb, queue_size=1)

        # ── 发布 ──
        self.cmd_pub  = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.goal_pub = rospy.Publisher('/exploration_goal', PointStamped, queue_size=1)

        # ── TF ──
        self.tf_buf   = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buf)

        # ── 状态 ──
        self.current_map = None
        self.state = 'IDLE'          # IDLE | ROTATE | FORWARD
        self.target_world = None     # (x, y) 目标世界坐标
        self.last_progress_time = rospy.Time.now()
        self.last_goal_time = rospy.Time.now()
        self.last_x = None
        self.last_y = None

        rospy.loginfo("🚀 SimpleExplorer 已启动 | 分工会作模式")

    # ── 回调：地图更新 ──────────────────────────────
    def map_cb(self, msg: OccupancyGrid):
        if (self.current_map is None or
            msg.info.width  != self.current_map.info.width or
            msg.info.height != self.current_map.info.height):
            rospy.loginfo(f"地图更新: {msg.info.width}x{msg.info.height} "
                          f"@ {msg.info.resolution:.2f}m/px")
        self.current_map = msg

    # ── 获取机器人位置 ──────────────────────────────
    def get_robot_pose(self):
        try:
            t = self.tf_buf.lookup_transform('map', 'camera_link',
                                             rospy.Time(0),
                                             rospy.Duration(0.5))
            return (t.transform.translation.x,
                    t.transform.translation.y,
                    self._yaw_from_quat(t.transform.rotation))
        except Exception as e:
            rospy.logwarn_throttle(5.0, f"TF 获取失败: {e}")
            return None

    @staticmethod
    def _yaw_from_quat(q):
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny, cosy)

    # ── 找前沿 ──────────────────────────────────────
    def find_frontiers(self, rx, ry, map_msg):
        """返回前沿簇的质心列表 [(x, y), ...]"""
        data = np.array(map_msg.data, dtype=np.int8)
        w = map_msg.info.width
        h = map_msg.info.height
        res = map_msg.info.resolution
        ox, oy = map_msg.info.origin.position.x, map_msg.info.origin.position.y

        # 只处理机器人周围区域（加速）
        search_cells = int(SEARCH_RADIUS / res)
        rx_cell = int((rx - ox) / res)
        ry_cell = int((ry - oy) / res)
        x_min = max(0, rx_cell - search_cells)
        x_max = min(w, rx_cell + search_cells)
        y_min = max(0, ry_cell - search_cells)
        y_max = min(h, ry_cell + search_cells)

        # 找前沿单元格（值为 0 且邻接 -1）
        frontier_cells = set()
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                idx = y * w + x
                if data[idx] == 0:  # 空闲
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),
                                   (-1,-1),(-1,1),(1,-1),(1,1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            if data[ny * w + nx] == -1:  # 未知
                                frontier_cells.add((x, y))
                                break

        if len(frontier_cells) < FRONTIER_MIN_SIZE:
            return []

        # BFS 聚类
        frontier_cells = set(frontier_cells)
        clusters = []
        while frontier_cells:
            start = frontier_cells.pop()
            cluster = [start]
            q = deque([start])
            while q:
                cx, cy = q.popleft()
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nb = (cx + dx, cy + dy)
                    if nb in frontier_cells:
                        frontier_cells.remove(nb)
                        cluster.append(nb)
                        q.append(nb)
            if len(cluster) >= FRONTIER_MIN_SIZE:
                clusters.append(cluster)

        # 计算质心（世界坐标）
        centroids = []
        for cl in clusters:
            avg_x = sum(c[0] for c in cl) / len(cl)
            avg_y = sum(c[1] for c in cl) / len(cl)
            wx = avg_x * res + ox
            wy = avg_y * res + oy
            centroids.append((wx, wy))

        return centroids

    # ── 选最近前沿 ──────────────────────────────────
    def pick_frontier(self, rx, ry, frontiers):
        if not frontiers:
            return None
        # 最近的
        best = min(frontiers,
                   key=lambda f: (f[0]-rx)**2 + (f[1]-ry)**2)
        return best

    # ── 状态机执行 ──────────────────────────────────
    def execute(self, rx, ry, ryaw):
        now = rospy.Time.now()

        # 卡住检测
        if self.last_x is not None:
            dist_moved = math.sqrt((rx - self.last_x)**2 + (ry - self.last_y)**2)
            if dist_moved < STUCK_THRESH:
                if (now - self.last_progress_time).to_sec() > GOAL_TIMEOUT:
                    rospy.loginfo("⏰ 目标超时/卡住，重新选目标")
                    self.target_world = None
                    self.state = 'IDLE'
                    self.last_progress_time = now
            else:
                self.last_progress_time = now
        self.last_x = rx
        self.last_y = ry

        # 没有目标 → 找前沿
        if self.target_world is None and self.current_map is not None:
            frontiers = self.find_frontiers(rx, ry, self.current_map)
            if frontiers:
                self.target_world = self.pick_frontier(rx, ry, frontiers)
                self.state = 'ROTATE'
                self.last_progress_time = now
                self.last_goal_time = now
                rospy.loginfo(f"🎯 新目标: ({self.target_world[0]:.2f}, {self.target_world[1]:.2f})")
                # 发布目标标记
                goal = PointStamped()
                goal.header.stamp = now
                goal.header.frame_id = 'map'
                goal.point.x = self.target_world[0]
                goal.point.y = self.target_world[1]
                self.goal_pub.publish(goal)
            else:
                # 没有前沿 → 原地旋转找新区域
                rospy.logdebug("🔍 附近无前沿，旋转探索")
                twist = Twist()
                twist.angular.z = TURN_SPEED * 0.5
                self.cmd_pub.publish(twist)
                return

        if self.target_world is None:
            # 没地图也没目标，等待
            return

        # 计算到目标的距离和角度
        gx, gy = self.target_world
        dx = gx - rx
        dy = gy - ry
        dist = math.sqrt(dx*dx + dy*dy)
        target_angle = math.atan2(dy, dx)
        angle_diff = self._normalize_angle(target_angle - ryaw)

        # 目标到达
        if dist < GOAL_REACHED_DIST:
            rospy.loginfo(f"✅ 到达目标")
            self.target_world = None
            self.state = 'IDLE'
            self.cmd_pub.publish(Twist())  # 停止
            return

        # 目标超时
        if (now - self.last_goal_time).to_sec() > GOAL_TIMEOUT * 2:
            rospy.loginfo("⏰ 全局目标超时")
            self.target_world = None
            self.state = 'IDLE'
            return

        # 状态机
        twist = Twist()

        if self.state == 'ROTATE':
            if abs(angle_diff) < ANGLE_TOLERANCE:
                self.state = 'FORWARD'
                rospy.logdebug("→ FORWARD")
            else:
                twist.angular.z = TURN_SPEED if angle_diff > 0 else -TURN_SPEED

        elif self.state == 'FORWARD':
            # 角度偏离太大 → 重新旋转
            if abs(angle_diff) > ANGLE_TOLERANCE * 2:
                self.state = 'ROTATE'
                rospy.logdebug("→ ROTATE (偏离)")
            else:
                twist.linear.x = FORWARD_SPEED
                # 微调角度
                twist.angular.z = angle_diff * 0.8

        self.cmd_pub.publish(twist)

    @staticmethod
    def _normalize_angle(a):
        while a > math.pi:
            a -= 2 * math.pi
        while a < -math.pi:
            a += 2 * math.pi
        return a

    # ── 主循环 ──────────────────────────────────────
    def spin(self):
        rate = rospy.Rate(EXPLORE_RATE)
        while not rospy.is_shutdown():
            pose = self.get_robot_pose()
            if pose is not None:
                self.execute(*pose)
            else:
                # 没有位姿 → 停车等待
                self.cmd_pub.publish(Twist())
            rate.sleep()


if __name__ == '__main__':
    explorer = SimpleExplorer()
    explorer.spin()
