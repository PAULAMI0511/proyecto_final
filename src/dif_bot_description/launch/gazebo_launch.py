import os
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_path = get_package_share_directory('dif_bot_description')
    xacro_file = os.path.join(pkg_path, 'urdf', 'dif_bot_description.urdf.xacro')
    world_file = os.path.join(pkg_path, 'worlds', 'mundo_sensores.sdf')
    # Procesar archivo Xacro a XML URDF
    use_ros2_control = LaunchConfiguration('use_ros2_control')
    robot_description_raw = ParameterValue(
        Command(['xacro ', xacro_file, ' use_ros2_control:=', use_ros2_control]),
        value_type=str
    )

    # Publicador del estado del robot
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw, 'use_sim_time': True}]
    )

    # Lanzar Gazebo Ignition con un mundo vacío
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
                launch_arguments={'gz_args': f'-r {world_file}'}.items(),
    )

    # Crear la entidad del robot en Gazebo usando ros_gz_sim create
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'dif_bot',
            '-z', '0.1'
        ]
    )

    # Puente Gazebo -> ROS 2
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/scan3d/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',        
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
        ]
    )

        # Filtro EKF: fusiona odometría de ruedas + IMU
    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[os.path.join(pkg_path, 'config', 'ekf.yaml'), {'use_sim_time': True}],
        remappings=[('odometry/filtered', 'odom_filtered')]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_ros2_control', default_value='false'),
        node_robot_state_publisher,
        gazebo,
        spawn_entity,
        bridge,
        ekf
    ])
