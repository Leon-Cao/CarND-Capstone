## Capstone Project Summary
### Implementation Introduce
#### Waypoint Update
 * LOOKAHEAD_WPS was changed from 200 to 130 to reduce the caculation of traffic light detection on Camera image.
 * Waypoint update is running on 50Hz frequency and subscriber `/current_pose`, `/base_waypoints` and `/traffic_waypoint`.
   * Function `pose_cb()` will be invoked when there is new `/current_pose` message. `pose_cb()` update current pose of vehicle. Function `get_closest_waypoint_idx()` to update the waypoints ahead of vehicle.
   * Function `waypoints_cb()` is the callback for `/base_waypoints` to get all waypoints of simulator or site. 
   * Function `traffic_cb()` is the callback for `/traffic_waypoint` for the stop waypoints of traffic light. Function `waypoints_before_stopline()` is processing the velocity of vehicle if the traffic light is red. The decrease velocity is caculated by `math.sqrt(2 * MAX_DECEL * dist)` and MAX_DECEL equals to 0.5. 
 * There is on publishing message `final_waypoints`. The function `publish_waypoints()` is response for publish this message. If the `stopline_waypoint_idx` is in the array of waypoints ahead of vehicle, then updated the waypoints array by `waypoints_before_stopline()`. Otherwise will return the current waypoint to 130 farther waypoints. 
#### Twist Control
 * PID Control is reused provided module.
   * PID parameters: P = 0.3, i = 0.0001 and d = 0. And tau = 0.5, ts = 0.02
   * For PID control: It will check if dbw_enable is set, if not set return 0. 
    * `vel` is checked if larger than target velocity. If it is larger then call vel_lpf.filt() to get limited velocity.
    * `steering` is updated yaw_controller.get_steering(linear_vel, angular_vel, vel)
    * `throttle` is updated throttle_controller.step(vel_error, sample_time) and should limited the max throttle not larger than requst.
    * `brake` should be set 700NS when velocity is close to 0 to make Carla stop.
 * DBW Node
  * Message `/vehicle/dbw_enabled` is subscribed to check if DBW should be enabled.
  * Message `/twist_cmd` is subscribed to update linear velocity and angular velocity for PID control.
  * Message `/current_velocity` is subscribed to update linear velocity.
  * Then PID `control()` function will be invoked. And publish the `/current_velocity` for velocity control; publish the `/vehicle/throttle_cmd` for speed up; publish `/vehicle/brake_cmd` for brake power.
#### Traffic Light Detection
 * Our traffic light detection module is SSD mobilenet. There are two trained models, one for simulator and can identify the traffic light correctly more than 90%; the other for Carla can identify correctly > 70%. 
 * It is to hard to prepare Tensorflow 1.3 for new model training. The tensorflow version in Carla is too old and it is very hard to merge latest models to Carla. We waste a lot of time on this activity. Hope Carla can update tensorflow!!!
 * tl_detector is callback triggered programm. `save_img()` for debug purpose. `image_cb()` will call `process_traffic_lights()` to identify the image of traffic light and publish `/traffic_waypoint` if the light is red. `image_cb()` is invoked by message `/image_raw` for Carla test OR message `/image_color` for simulator.
  * Subscribe message `/current_pose` is to get current pose of vechile. 
  * Subscribe message `/base_waypoints` is to get all waypoints.
  * Subscribe message `/vehicle/traffic_lights` is to get the light waypoint and call `get_light_state()` and it calls `get_classification()` which is implemented in tl_classifier.py to identify the light color.
  * tl_detector will check if current is for site test (Carla), if yes, will use the SSD model for site test. Otherwise will call for SSD model for simulator.
  
### Suggestion
 * For "ROS in VM + Simulator", the communication latency between VM and simulator is quite big and affect student to know if his code is correct. Install ROS to ubuntu is quite easy and there is no any delay between ROS+Simulator. At least should describe this limitation and mention ROS+ubuntu is a good choice. Then it will not waste debug time.

-------------------------------------------
This is the project repo for the final project of the Udacity Self-Driving Car Nanodegree: Programming a Real Self-Driving Car. For more information about the project, see the project introduction [here](https://classroom.udacity.com/nanodegrees/nd013/parts/6047fe34-d93c-4f50-8336-b70ef10cb4b2/modules/e1a23b06-329a-4684-a717-ad476f0d8dff/lessons/462c933d-9f24-42d3-8bdc-a08a5fc866e4/concepts/5ab4b122-83e6-436d-850f-9f4d26627fd9).

Please use **one** of the two installation options, either native **or** docker installation.

### Native Installation

* Be sure that your workstation is running Ubuntu 16.04 Xenial Xerus or Ubuntu 14.04 Trusty Tahir. [Ubuntu downloads can be found here](https://www.ubuntu.com/download/desktop).
* If using a Virtual Machine to install Ubuntu, use the following configuration as minimum:
  * 2 CPU
  * 2 GB system memory
  * 25 GB of free hard drive space

  The Udacity provided virtual machine has ROS and Dataspeed DBW already installed, so you can skip the next two steps if you are using this.

* Follow these instructions to install ROS
  * [ROS Kinetic](http://wiki.ros.org/kinetic/Installation/Ubuntu) if you have Ubuntu 16.04.
  * [ROS Indigo](http://wiki.ros.org/indigo/Installation/Ubuntu) if you have Ubuntu 14.04.
* [Dataspeed DBW](https://bitbucket.org/DataspeedInc/dbw_mkz_ros)
  * Use this option to install the SDK on a workstation that already has ROS installed: [One Line SDK Install (binary)](https://bitbucket.org/DataspeedInc/dbw_mkz_ros/src/81e63fcc335d7b64139d7482017d6a97b405e250/ROS_SETUP.md?fileviewer=file-view-default)
* Download the [Udacity Simulator](https://github.com/udacity/CarND-Capstone/releases).

### Docker Installation
[Install Docker](https://docs.docker.com/engine/installation/)

Build the docker container
```bash
docker build . -t capstone
```

Run the docker file
```bash
docker run -p 4567:4567 -v $PWD:/capstone -v /tmp/log:/root/.ros/ --rm -it capstone
```

### Port Forwarding
To set up port forwarding, please refer to the "uWebSocketIO Starter Guide" found in the classroom (see Extended Kalman Filter Project lesson).

### Usage

1. Clone the project repository
```bash
git clone https://github.com/udacity/CarND-Capstone.git
```

2. Install python dependencies
```bash
cd CarND-Capstone
pip install -r requirements.txt
```
3. Make and run styx
```bash
cd ros
catkin_make
source devel/setup.sh
roslaunch launch/styx.launch
```
4. Run the simulator

### Real world testing
1. Download [training bag](https://s3-us-west-1.amazonaws.com/udacity-selfdrivingcar/traffic_light_bag_file.zip) that was recorded on the Udacity self-driving car.
2. Unzip the file
```bash
unzip traffic_light_bag_file.zip
```
3. Play the bag file
```bash
rosbag play -l traffic_light_bag_file/traffic_light_training.bag
```
4. Launch your project in site mode
```bash
cd CarND-Capstone/ros
roslaunch launch/site.launch
```
5. Confirm that traffic light detection works on real life images

### Other library/driver information
Outside of `requirements.txt`, here is information on other driver/library versions used in the simulator and Carla:

Specific to these libraries, the simulator grader and Carla use the following:

|        | Simulator | Carla  |
| :-----------: |:-------------:| :-----:|
| Nvidia driver | 384.130 | 384.130 |
| CUDA | 8.0.61 | 8.0.61 |
| cuDNN | 6.0.21 | 6.0.21 |
| TensorRT | N/A | N/A |
| OpenCV | 3.2.0-dev | 2.4.8 |
| OpenMP | N/A | N/A |

We are working on a fix to line up the OpenCV versions between the two.
