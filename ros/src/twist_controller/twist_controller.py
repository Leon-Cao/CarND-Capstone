from pid import PID
from lowpass import LowPassFilter
from yaw_controller import YawController

import rospy

GAS_DENSITY = 2.858
ONE_MPH = 0.44704
TARGET_VEL_M_S = 5 #2.78

class Controller(object):
    def __init__(self, vehicle_mass, fuel_capacity, brake_deadband, decel_limit,
                       accel_limit, wheel_radius, wheel_base, steer_ratio,
                       max_lat_accel, max_steer_angle):
        # TODO: Implement
        self.min_vel = 0.1

        self.yaw_controller = YawController(wheel_base, steer_ratio, self.min_vel, max_lat_accel, max_steer_angle)

        # Coefficients for PID Controller
        p = 0.3
        i = 0.0001
        d = 0.

        min_throttle = 0.
        max_throttle = 0.4

        # initialize PID controller
        self.throttle_controller = PID(p, i, d, min_throttle, max_throttle)

        tau = 0.5
        ts = .02

        self.vel_lpf = LowPassFilter(tau, ts)
        self.vehicle_mass = vehicle_mass
        self.fuel_capacity = fuel_capacity
        self.brake_deadband = brake_deadband
        self.decel_limit = decel_limit
        self.accel_limit = accel_limit
        self.wheel_radius = wheel_radius

        self.last_time = rospy.get_time()

    def control(self, current_vel, dbw_enabled, linear_vel, angular_vel):
        # TODO: Change the arg, kwarg list to suit your needs

        # if dbw not enabled, reset controller
        if not dbw_enabled:
            self.throttle_controller.reset()
            return 0., 0., 0.
        # filter current velocity
        if linear_vel > TARGET_VEL_M_S:  # 2.78 m/s -> 10 km/h
            vel = self.vel_lpf.filt(current_vel)
        else:
            vel = current_vel

        steering = self.yaw_controller.get_steering(linear_vel, angular_vel, vel)
        vel_error = linear_vel - vel

        current_time = rospy.get_time()
        sample_time = current_time - self.last_time
        self.last_time = current_time

        throttle = self.throttle_controller.step(vel_error, sample_time)
        if linear_vel < TARGET_VEL_M_S:  # 2.78 m/s -> 10 km/h
            throttle = 0.25 * throttle

        brake = 0.

        if linear_vel == 0. and vel < self.min_vel:
            throttle = 0.
            brake = 700
            steering = 0.
        elif throttle < .1 and vel_error < 0:
            throttle = 0
            decel = max(vel_error, self.decel_limit)
            brake = abs(decel) * self.vehicle_mass * self.wheel_radius
            if brake < 700.:
                brake = 700.
        # Return throttle, brake, steer
        # rospy.loginfo("Control (%s, %s, %s) -> throttle: %s, brake: %s, steer: %s", linear_vel, current_vel, vel, throttle, brake, steering)
        return throttle, brake, steering

