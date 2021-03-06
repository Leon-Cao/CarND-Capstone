#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml
from scipy.spatial import KDTree
import rospkg
import matplotlib.pyplot as plt

STATE_COUNT_THRESHOLD = 2
TARGET_LOOKAHEAD_WPS = 130
DISTANCE_TRAFFIC_LIGHT = 70

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector')

        self.pose = None
        self.waypoints = None
        self.camera_image = None
        self.lights = []
        current_path = rospkg.RosPack().get_path('tl_detector')
        self.img_save_path = current_path + '/debug_img/'
        self.img_save_count=0
        self.waypoints_2d = None
        self.waypoint_tree = None
        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)
        self.is_site = self.config["is_site"]
        self.light_classifier = TLClassifier(self.is_site)


        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        '''
        /vehicle/traffic_lights provides you with the location of the traffic light in 3D map space and
        helps you acquire an accurate ground truth data source for the traffic light
        classifier by sending the current color state of all traffic lights in the
        simulator. When testing on the vehicle, the color state will not be available. You'll need to
        rely on the position of the light and the camera image to predict it.
        '''
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)
        sub6 = None
        if self.is_site: 
            rospy.loginfo("tl_detection capture img from image_raw")
            sub6 = rospy.Subscriber('/image_raw', Image, self.image_cb)
        else:
            rospy.loginfo("tl_detection capture img from image_color")
            sub6 = rospy.Subscriber('/image_color', Image, self.image_cb)


        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        self.bridge = CvBridge()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0

        rospy.spin()
			
    def pose_cb(self, msg):
        self.pose = msg
        #rospy.loginfo("tl_detector pose_cb: current_pose.x = %s - .y=%s", self.pose.pose.position.x, self.pose.pose.position.y)
    def waypoints_cb(self, waypoints):
        self.waypoints = waypoints
        # Setup the Kd Tree which has log(n) complexity
        if not self.waypoints_2d:
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in
                                 waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)
            #rospy.loginfo("waypoints_2d = %s", waypoints_2d)

    def traffic_cb(self, msg):
        self.lights = msg.lights

    def save_img(self, image):
        self.img_save_count += 1
        image_name = self.img_save_path + str(self.img_save_count)
        plt.imsave(image_name, image)
    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light's stop line to /traffic_waypoint

        Args:
            msg (Image): image from car-mounted camera

        """
        self.has_image = True
        self.camera_image = msg
		
        light_wp, state = self.process_traffic_lights()
        #rospy.loginfo("tl_detector.py Closest light wp:" + state)

        '''
        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.
        '''
        if self.state != state:
            self.state_count = 0
            self.state = state
        elif self.state_count >= STATE_COUNT_THRESHOLD:
            self.last_state = self.state
            light_wp = light_wp if state == TrafficLight.RED else -1
            self.last_wp = light_wp
            self.upcoming_red_light_pub.publish(Int32(light_wp))
        else:
            self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        self.state_count += 1

        self.has_image == False

    def get_closest_waypoint(self, x, y):
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to

        Returns:
            int: index of the closest waypoint in self.waypoints

        """
        #TODO implement
        closest_idx = None
        if self.waypoint_tree:
            closest_idx = self.waypoint_tree.query([x,y], 1)[1]

        return closest_idx

    def get_light_state(self, light):
        """Determines the current color of the traffic light

        Args:
            light (TrafficLight): light to classify

        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        if(not self.has_image):
           self.prev_light_loc = None
           return False

        cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "rgb8")
        # debug for save image
        #self.save_img(cv_image)
        #Get classification
        return self.light_classifier.get_classification(cv_image)

    def process_traffic_lights(self):
        """Finds closest visible traffic light, if one exists, and determines its
            location and color

        Returns:
            int: index of waypoint closes to the upcoming stop line for a traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        light = None
        light_wp_idx = None

        # List of positions that correspond to the line to stop in front of for a given intersection
        stop_line_positions = self.config['stop_line_positions']
        if self.pose and self.waypoints:
            car_position = self.get_closest_waypoint(self.pose.pose.position.x, self.pose.pose.position.y)

            #TODO find the closest visible traffic light (if one exists)
            if not car_position:
                return -1, TrafficLight.UNKNOWN

            min_wp_diff = min(len(self.waypoints.waypoints), TARGET_LOOKAHEAD_WPS)
            tmp_wp_idx = None
            for i, tmp_light in enumerate(self.lights):
                stop_line = stop_line_positions[i]
                tmp_wp_idx = self.get_closest_waypoint(stop_line[0], stop_line[1])
				
                d = tmp_wp_idx - car_position
                if d >= 0 and d < min_wp_diff:
                    min_wp_diff = d
                    light = tmp_light
                    light_wp_idx = tmp_wp_idx

        if light:
            state = self.get_light_state(light)
            return light_wp_idx, state
        else:
            return -1, TrafficLight.UNKNOWN

if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')
