import rospy
from sensor_msgs.msg import Joy
from mavros_msgs.msg import BatteryStatus, State, OverrideRCIn
from mavros_msgs.srv import CommandBool, SetMode
from cv_bridge import CvBridge, CvBridgeError

joystick = {'arm': 2, 'disarm': 3, 'failsafe': 0, 'auto': 4, 'manual': 5, 'x': 0, 'y': 1, 'z': 3, 'yaw': 2}
xbox     = {'arm': 0, 'disarm': 1, 'failsafe': 8, 'auto': 2, 'manual': 3, 'x': 3, 'y': 4, 'z': 1, 'yaw': 0}
ctrl = xbox # Set this variable to the joystick you are currently using

# This is a helper class that encodes all of the callback functions for a drone
class Drone():
    def __init__(self):
        # ROS state variables
        self.buttons = [0, 0, 0, 0, 0, 0, 0, 0]
        self.axes = [0, 0, 0, 0, 0, 0, 0, 0]
        self.mode = 0
        self.armed = False
        self.flight_mode = ''
        self.voltage = 0
        self.current = 0
        self.battery_remaining = 0
        self.latitude = None
        self.longitude = None
        self.altitude = 0.0
        self.old_z = 1000
        self.just_armed = False

        # ROS publishers
        self.pub_rc = rospy.Publisher('/drone/rc/override', OverrideRCIn, queue_size=10)

        # ROS subscribers
        self.sub_joy = rospy.Subscriber('/drone/joy', Joy, self.joy_callback)
        self.sub_state = rospy.Subscriber('/drone/state', State, self.state_callback)
        self.sub_battery = rospy.Subscriber('/drone/battery', BatteryStatus, self.battery_callback)

        # ROS services
        self.srv_arm = rospy.ServiceProxy('/drone/cmd/arming', CommandBool)
        self.srv_mode = rospy.ServiceProxy('/drone/set_mode', SetMode)

    """ Publishes to the 8 RC channels """
    def publish_rc(self, channels):
        commands = OverrideRCIN(channels=channels)
        self.pub_rc.publish(commands)

    """ Joystick control (can be overriden) """
    def fly_joystick(self, x=0, y=0, z=0, yaw=0):
        if self.buttons:
            # Arm drone
            if self.buttons[0] and not self.armed:
                self.srv_mode(0, '2')
                self.srv_arm(True)
                self.just_armed = True
                self.old_z = self.axes[1]
                print "Arming drone"

            # Disarm drone
            if self.buttons[1]:
                self.srv_arm(False)
                print "Disarming drone"

        if self.armed:
            x = 1500 - self.axes[ ctrl['x'] ] * 300
            y = 1500 - self.axes[ ctrl['y'] ] * 300
            z = 1500 + self.axes[ ctrl['z'] ] * 500
            yaw = 1500 - self.axes[ ctrl['yaw'] ] * 300

            if self.just_armed:
                z = 1000
                if abs(self.axes[ ctrl['z'] ]) > 0.1:
                    self.just_armed = False

            if z < 1200:
                z = 1000
            elif z < 1450:
                z = 1300
            elif z > 1650:
                z = 1750
            else:
                z = 1500

            if abs(x - 1500) < 50:
                x = 1500
            if abs(y - 1500) < 50:
                y = 1500

            channels = [x, y, z, yaw, 0, 0, 1250, 0]
            self.publish_rc(channels)

    """ Various callback functions for each ROS topic """
    def joy_callback(self, data):
        self.axes = data.axes
        self.buttons = data.buttons

    def state_callback(self, data):
        self.armed = data.armed
        self.flight_mode = data.mode

    def battery_callback(self, data):
        self.voltage = data.voltage
        self.current = data.current
        self.battery_remaining = data.remaining

    def gps_callback(self, data):
        self.latitude = data.latitude
        self.longitude = data.longitude

    def altitude_callback(self, data):
        self.altitude = data