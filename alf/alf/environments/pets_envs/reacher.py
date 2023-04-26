from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os

import numpy as np
from gym import utils
from gym.envs.mujoco import mujoco_env

class Reacher3DEnv(mujoco_env.MujocoEnv, utils.EzPickle):
    def __init__(self):
        """加载xml文件"""
        self.viewer = None
        self.goal = np.zeros(3)

        self.num_timesteps = 0
        utils.EzPickle.__init__(self)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        mujoco_env.MujocoEnv.__init__(self, os.path.join(dir_path, 'assets/reacher3d.xml'), 2)

    def step(self, a):
        self.num_timesteps += 1
        self.do_simulation(a, self.frame_skip)
        ob = self._get_obs()

        # % 设定稀疏奖励
        # reward = -np.sum(np.square(self.get_EE_pos(ob[None]) - self.goal))
        # reward -= 0.01 * np.square(a).sum()
        reward_ctrl = 0.0001 * -np.square(a).sum()

        success = False
        if np.sqrt(np.sum(np.square(self.get_EE_pos(ob[None]) - self.goal))) <= 0.25:  # [None]表示全取
            success = True
        reward = reward_ctrl + float(success)

        done = self.num_timesteps >= 100
        info = {'is_success': success}
        return ob, reward, done, info

    def viewer_setup(self):
        self.viewer.cam.trackbodyid = 1
        self.viewer.cam.distance = 2.5
        self.viewer.cam.elevation = -30
        self.viewer.cam.azimuth = 270

    def reset_model(self):
        """不同算法有不同的初始化设定方式，但本质都是一样的"""
        qpos = np.copy(self.init_qpos)
        qpos[-3:] += np.random.normal(loc=0, scale=0.1, size=[3])  # 给予agent和目标初始化位置随机性
        self.goal = qpos[-3:]  # 设置目标为方向

        qvel = np.copy(self.init_qvel)
        qvel[-3:] = 0

        self.set_state(qpos, qvel)
        return self._get_obs()

    def _get_obs(self):
        """状态：10 + 7. 无 tips_arm，object，goal"""
        return np.concatenate([
            self.data.qpos.flat,   # 10维
            self.data.qvel.flat[:-3],   # 7维
        ])

    def get_EE_pos(self, states):
        theta1, theta2, theta3, theta4, theta5, theta6, theta7 = \
            states[:, :1], states[:, 1:2], states[:, 2:3], states[:, 3:4], states[:, 4:5], states[:, 5:6], states[:, 6:]

        rot_axis = np.concatenate([np.cos(theta2) * np.cos(theta1), np.cos(theta2) * np.sin(theta1), -np.sin(theta2)], axis=1)
        rot_perp_axis = np.concatenate([-np.sin(theta1), np.cos(theta1), np.zeros(theta1.shape)], axis=1)
        cur_end = np.concatenate([
            0.1 * np.cos(theta1) + 0.4 * np.cos(theta1) * np.cos(theta2),
            0.1 * np.sin(theta1) + 0.4 * np.sin(theta1) * np.cos(theta2) - 0.188,
            -0.4 * np.sin(theta2)
        ], axis=1)

        for length, hinge, roll in [(0.321, theta4, theta3), (0.16828, theta6, theta5)]:
            perp_all_axis = np.cross(rot_axis, rot_perp_axis)
            x = np.cos(hinge) * rot_axis
            y = np.sin(hinge) * np.sin(roll) * rot_perp_axis
            z = -np.sin(hinge) * np.cos(roll) * perp_all_axis
            new_rot_axis = x + y + z
            new_rot_perp_axis = np.cross(new_rot_axis, rot_axis)
            new_rot_perp_axis[np.linalg.norm(new_rot_perp_axis, axis=1) < 1e-30] = \
                rot_perp_axis[np.linalg.norm(new_rot_perp_axis, axis=1) < 1e-30]
            new_rot_perp_axis /= np.linalg.norm(new_rot_perp_axis, axis=1, keepdims=True)
            rot_axis, rot_perp_axis, cur_end = new_rot_axis, new_rot_perp_axis, cur_end + length * new_rot_axis

        return cur_end

    def reset(self):
        self.num_timesteps = 0
        return super().reset()

if __name__ == '__main__':
    env = Reacher3DEnv()
    done = False
    obs = env.reset()
    counter = 0
    import pdb;

    pdb.set_trace()
    while not done:
        obs, reward, done, info = env.step(env.action_space.sample())
        counter += 1
        print(obs, reward, done, info)
    print(counter)
